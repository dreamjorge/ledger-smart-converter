from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
from services.db_service import DatabaseService


def _empty_stats() -> Dict[str, Any]:
    return {
        "total": 0,
        "categorized": 0,
        "uncategorized": 0,
        "coverage_pct": 0,
        "category_populated": 0,
        "category_pct": 0,
        "total_spent": 0.0,
        "type_counts": {},
        "categories": {},
        "category_spending": {},
        "monthly_spending_trends": {},
    }


def _normalize_analytics_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize analytics inputs once at the service boundary.

    The goal is to keep downstream aggregation code working against a stable
    frame shape regardless of whether the input originated from CSV loading,
    SQLite, or a test fixture with partial columns.
    """
    normalized = df.copy()

    if "date" in normalized.columns:
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
    if "amount" in normalized.columns:
        normalized["amount"] = pd.to_numeric(normalized["amount"], errors="coerce")
    else:
        normalized["amount"] = pd.Series(
            [0.0] * len(normalized), index=normalized.index, dtype="float64"
        )

    if "type" in normalized.columns:
        normalized["type"] = (
            normalized["type"].astype("object").where(normalized["type"].notna(), None)
        )
    else:
        normalized["type"] = pd.Series(
            [None] * len(normalized), index=normalized.index, dtype="object"
        )

    for column in ("destination_name", "category_name", "tags"):
        if column not in normalized.columns:
            normalized[column] = pd.Series(
                [None] * len(normalized), index=normalized.index, dtype="object"
            )

    return normalized


def is_categorized(destination_name) -> bool:
    """Check if a destination_name represents a categorized transaction.

    A transaction is considered categorized if its destination_name:
    1. Is not None/NaN
    2. Is not an empty string
    3. Contains a colon (e.g., "Expenses:Food", "Assets:Cash")

    Args:
        destination_name: The destination_name value to check (can be str, None, NaN, etc.)

    Returns:
        True if categorized, False otherwise

    Examples:
        >>> is_categorized("Expenses:Food")
        True
        >>> is_categorized("Assets:Cash")
        True
        >>> is_categorized("PlainName")
        False
        >>> is_categorized("")
        False
        >>> is_categorized(None)
        False
        >>> is_categorized(pd.NA)
        False
    """
    if pd.isna(destination_name):
        return False
    if destination_name == "":
        return False
    if ":" not in str(destination_name):
        return False
    return True


def calculate_categorization_stats(
    df: Optional[pd.DataFrame],
    period: Optional[str] = None,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Optional[Dict[str, Any]]:
    """Calculate categorization statistics for transactions.

    Analyzes transaction data to provide statistics about categorization coverage,
    spending patterns, and category breakdowns.

    Categorization Rules:
        A transaction is considered "categorized" if its destination_name:
        - Is not None/NaN
        - Is not an empty string
        - Contains a colon (e.g., "Expenses:Food", "Assets:Cash")

        Uses the is_categorized() helper to avoid double-counting edge cases.

    Args:
        df: DataFrame containing transaction data
        period: Optional period tag to filter by (e.g., "2024-01")
        start_date: Optional start date for date range filtering
        end_date: Optional end date for date range filtering

    Returns:
        Dictionary with categorization statistics, or None if df is None.
        Keys include: total, categorized, uncategorized, coverage_pct,
        category_populated, category_pct, total_spent, type_counts,
        categories, category_spending, monthly_spending_trends

    Note:
        - Period filtering is ignored if date range filters are present
        - Monthly trends only include withdrawal transactions from Expenses:* categories
    """
    if df is None:
        return None
    if df.empty:
        return _empty_stats()

    df = _normalize_analytics_frame(df)

    # Apply date range filtering if provided
    if start_date and "date" in df.columns:
        df = df[df["date"] >= start_date]
    if end_date and "date" in df.columns:
        df = df[df["date"] <= end_date]

    # If date range filtering was applied and resulted in empty df, return early
    if df.empty:
        return _empty_stats()

    # Apply period filtering ONLY if no date range filtering was applied
    if not (start_date or end_date) and period and "tags" in df.columns:
        df = df[df["tags"].str.contains(f"period:{period}", na=False)]
        if df.empty:  # If after filtering, df is empty, return empty stats
            return _empty_stats()

    total = len(df)
    categorized = df["destination_name"].apply(is_categorized).sum()
    uncategorized = total - categorized

    has_category = df["category_name"].notna() & (df["category_name"] != "")
    category_populated = has_category.sum()

    total_spent = df[df["type"] == "withdrawal"]["amount"].dropna().sum()

    type_counts = df["type"].dropna().value_counts().to_dict()
    categories = {}
    category_spending = {}
    monthly_spending_trends = {}

    if "date" in df.columns:
        # Spending trends over time
        # Filter for withdrawal transactions
        withdrawals_df = df[df["type"] == "withdrawal"].copy()
        withdrawals_df.dropna(
            subset=["amount", "date", "destination_name"], inplace=True
        )

        # Extract main category from destination_name (e.g., "Expenses:Food" -> "Food")
        # Only consider entries that look like categories, i.e., contain a colon and start with "Expenses"
        withdrawals_df["main_category"] = withdrawals_df["destination_name"].apply(
            lambda x: (
                str(x).split(":")[1]
                if pd.notna(x) and ":" in str(x) and str(x).startswith("Expenses")
                else None
            )
        )
        withdrawals_df.dropna(subset=["main_category"], inplace=True)

        if not withdrawals_df.empty:
            withdrawals_df["date"] = pd.to_datetime(
                withdrawals_df["date"], errors="coerce"
            )
            withdrawals_df = withdrawals_df[withdrawals_df["date"].notna()]

        if not withdrawals_df.empty:
            withdrawals_df["year_month"] = withdrawals_df["date"].dt.to_period("M")

            monthly_trends = (
                withdrawals_df.groupby(["year_month", "main_category"])["amount"]
                .sum()
                .reset_index()
            )
            monthly_trends["year_month"] = monthly_trends["year_month"].astype(
                str
            )  # Convert Period to string for easier JSON serialization

            for _, row in monthly_trends.iterrows():
                month_cat = row["year_month"]
                category = row["main_category"]
                amount = row["amount"]
                if month_cat not in monthly_spending_trends:
                    monthly_spending_trends[month_cat] = {}
                monthly_spending_trends[month_cat][category] = (
                    monthly_spending_trends[month_cat].get(category, 0.0) + amount
                )

        for _, row in df.iterrows():
            dest = row["destination_name"]
            amt = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
            if pd.notna(dest) and ":" in str(dest):
                parts = str(dest).split(":")
                if len(parts) > 1 and parts[0] == "Expenses":
                    cat = parts[1]
                    categories[cat] = categories.get(cat, 0) + 1
                    if row.get("type") == "withdrawal":
                        category_spending[cat] = category_spending.get(cat, 0.0) + amt

    return {
        "total": total,
        "categorized": categorized,
        "uncategorized": uncategorized,
        "coverage_pct": (categorized / total * 100) if total > 0 else 0,
        "category_populated": category_populated,
        "category_pct": (category_populated / total * 100) if total > 0 else 0,
        "total_spent": total_spent,
        "type_counts": type_counts,
        "categories": categories,
        "category_spending": category_spending,
        "monthly_spending_trends": monthly_spending_trends,
    }


def calculate_categorization_stats_from_db(
    db_path,
    bank_id: Optional[str] = None,
    period: Optional[str] = None,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Dict[str, Any]:
    db = DatabaseService(db_path=db_path)

    query = """
        SELECT
            date,
            amount,
            COALESCE(transaction_type, 'withdrawal') AS type,
            destination_name,
            category AS category_name,
            tags
        FROM transactions
        WHERE 1=1
    """
    params = []
    if bank_id:
        query += " AND bank_id = ?"
        params.append(bank_id)
    if start_date is not None:
        query += " AND date >= ?"
        params.append(pd.to_datetime(start_date).strftime("%Y-%m-%d"))
    if end_date is not None:
        query += " AND date <= ?"
        params.append(pd.to_datetime(end_date).strftime("%Y-%m-%d"))
    if period and start_date is None and end_date is None:
        query += " AND tags LIKE ?"
        params.append(f"%period:{period}%")
    query += " ORDER BY date"

    rows = db.fetch_all(query, tuple(params))
    if not rows:
        return _empty_stats()

    df = pd.DataFrame(rows)
    return calculate_categorization_stats(
        df,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


def get_unified_dashboard_stats(
    db_path: Path,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Dict[str, Any]:
    """Calculate statistics for ALL bank accounts using direct SQL.

    Args:
        db_path: Path to the SQLite database.
        start_date: Optional start date for filtering.
        end_date: Optional end date for filtering.

    Returns:
        Unified statistics dictionary.
    """
    return calculate_categorization_stats_from_db(
        db_path=db_path,
        bank_id=None,  # None means all banks
        start_date=start_date,
        end_date=end_date,
    )
