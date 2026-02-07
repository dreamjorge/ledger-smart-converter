from typing import Any, Dict, Optional
import pandas as pd


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

    # Apply date range filtering if provided
    if start_date and "date" in df.columns:
        df = df[df["date"] >= start_date]
    if end_date and "date" in df.columns:
        df = df[df["date"] <= end_date]

    # If date range filtering was applied and resulted in empty df, return early
    if df.empty:
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

    # Apply period filtering ONLY if no date range filtering was applied
    if not (start_date or end_date) and period and "tags" in df.columns:
        df = df[df["tags"].str.contains(f"period:{period}", na=False)]
        if df.empty:  # If after filtering, df is empty, return empty stats
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

    total = len(df)
    if "destination_name" in df.columns:
        # Use is_categorized helper to avoid double-counting
        categorized = df["destination_name"].apply(is_categorized).sum()
        uncategorized = total - categorized
    else:
        categorized = 0
        uncategorized = total

    if "category_name" in df.columns:
        has_category = df["category_name"].notna() & (df["category_name"] != "")
        category_populated = has_category.sum()
    else:
        category_populated = 0

    total_spent = 0.0
    if "amount" in df.columns and "type" in df.columns:
        total_spent = df[df["type"] == "withdrawal"]["amount"].astype(float).sum()

    type_counts = df["type"].value_counts().to_dict() if "type" in df.columns else {}
    categories = {}
    category_spending = {}
    monthly_spending_trends = {}

    if "destination_name" in df.columns and "amount" in df.columns and "date" in df.columns:
        # Spending trends over time
        # Filter for withdrawal transactions
        withdrawals_df = df[df["type"] == "withdrawal"].copy()
        withdrawals_df["amount"] = pd.to_numeric(withdrawals_df["amount"], errors='coerce')
        withdrawals_df.dropna(subset=["amount", "date", "destination_name"], inplace=True)

        # Extract main category from destination_name (e.g., "Expenses:Food" -> "Food")
        # Only consider entries that look like categories, i.e., contain a colon and start with "Expenses"
        withdrawals_df["main_category"] = withdrawals_df["destination_name"].apply(
            lambda x: str(x).split(":")[1] if pd.notna(x) and ":" in str(x) and str(x).startswith("Expenses") else None
        )
        withdrawals_df.dropna(subset=["main_category"], inplace=True)


        if not withdrawals_df.empty:
            withdrawals_df["year_month"] = withdrawals_df["date"].dt.to_period("M")

            monthly_trends = withdrawals_df.groupby(["year_month", "main_category"])["amount"].sum().reset_index()
            monthly_trends["year_month"] = monthly_trends["year_month"].astype(str) # Convert Period to string for easier JSON serialization

            for _, row in monthly_trends.iterrows():
                month_cat = row["year_month"]
                category = row["main_category"]
                amount = row["amount"]
                if month_cat not in monthly_spending_trends:
                    monthly_spending_trends[month_cat] = {}
                monthly_spending_trends[month_cat][category] = monthly_spending_trends[month_cat].get(category, 0.0) + amount

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
