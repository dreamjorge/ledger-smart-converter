from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Any, Optional
import pandas as pd
from application.ports.transaction_repository import TransactionRepository

@dataclass(frozen=True)
class AnalyticsResult:
    total: int
    categorized: int
    uncategorized: int
    coverage_pct: float
    category_populated: int
    category_pct: float
    total_spent: float
    type_counts: Dict[str, int]
    categories: Dict[str, int]
    category_spending: Dict[str, float]
    monthly_spending_trends: Dict[str, Dict[str, float]]

class CalculateAnalytics:
    """
    Use case to calculate transaction analytics based on repository data.
    Encapsulates aggregation logic previously in analytics_service.
    """
    def __init__(self, repository: TransactionRepository):
        self.repository = repository

    def execute(
        self, 
        bank_id: Optional[str] = None, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        period: Optional[str] = None
    ) -> AnalyticsResult:
        # 1. Fetch data from repository
        tags = [f"period:{period}"] if period else []
        transactions = self.repository.find_by_criteria(
            bank_id=bank_id,
            start_date=start_date,
            end_date=end_date,
            tags=tags
        )

        if not transactions:
            return self._empty_result()

        # 2. Convert to DataFrame for aggregation (internal detail)
        # Using domain objects directly for aggregation is possible but 
        # less efficient than pandas for this specific legacy-aligned task.
        data = [
            {
                "date": t.date,
                "amount": t.amount,
                "type": t.transaction_type,
                "destination_name": t.destination_name,
                "category_name": t.category,
                "tags": t.tags
            } for t in transactions
        ]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        # 3. Calculation logic (mirroring analytics_service)
        total = len(df)
        
        def is_categorized(dest):
            if pd.isna(dest) or dest == "" or ":" not in str(dest):
                return False
            return True

        categorized = df["destination_name"].apply(is_categorized).sum()
        uncategorized = total - categorized

        has_category = df["category_name"].notna() & (df["category_name"] != "")
        category_populated = has_category.sum()

        total_spent = df[df["type"] == "withdrawal"]["amount"].dropna().sum()
        type_counts = df["type"].dropna().value_counts().to_dict()

        categories = {}
        category_spending = {}
        
        # Process categories for spending and counts
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

        # Monthly Trends
        monthly_spending_trends = {}
        withdrawals_df = df[df["type"] == "withdrawal"].copy()
        if not withdrawals_df.empty:
            withdrawals_df["main_category"] = withdrawals_df["destination_name"].apply(
                lambda x: str(x).split(":")[1] if pd.notna(x) and ":" in str(x) and str(x).startswith("Expenses") else None
            )
            withdrawals_df.dropna(subset=["main_category", "date"], inplace=True)
            
            if not withdrawals_df.empty:
                withdrawals_df["year_month"] = withdrawals_df["date"].dt.to_period("M").astype(str)
                trends = withdrawals_df.groupby(["year_month", "main_category"])["amount"].sum().reset_index()
                
                for _, row in trends.iterrows():
                    month_cat = row["year_month"]
                    category = row["main_category"]
                    amount = row["amount"]
                    if month_cat not in monthly_spending_trends:
                        monthly_spending_trends[month_cat] = {}
                    monthly_spending_trends[month_cat][category] = amount

        return AnalyticsResult(
            total=total,
            categorized=int(categorized),
            uncategorized=int(uncategorized),
            coverage_pct=(float(categorized) / total * 100) if total > 0 else 0.0,
            category_populated=int(category_populated),
            category_pct=(float(category_populated) / total * 100) if total > 0 else 0.0,
            total_spent=float(total_spent),
            type_counts=type_counts,
            categories=categories,
            category_spending=category_spending,
            monthly_spending_trends=monthly_spending_trends
        )

    def _empty_result(self) -> AnalyticsResult:
        return AnalyticsResult(
            total=0, categorized=0, uncategorized=0, coverage_pct=0.0,
            category_populated=0, category_pct=0.0, total_spent=0.0,
            type_counts={}, categories={}, category_spending={},
            monthly_spending_trends={}
        )
