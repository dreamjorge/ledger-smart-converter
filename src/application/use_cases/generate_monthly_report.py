from typing import List, Dict, Any, Optional
from datetime import date
from application.ports.transaction_repository import TransactionRepository
from domain.transaction import CanonicalTransaction

class GenerateMonthlyReport:
    def __init__(self, transaction_repo: TransactionRepository):
        self.transaction_repo = transaction_repo

    def execute(self, year: int, month: int, bank_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers and aggregates financial data for a monthly report.
        """
        # 1. Define date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) # Actually handled by repository logic usually
        else:
            end_date = date(year, month + 1, 1)
        
        # 2. Fetch transactions
        # We can use find_by_criteria but we need to ensure it handles the start/end correctly.
        # For simplicity, we'll fetch all and filter in memory if the repo is simple, 
        # but let's try to use find_by_criteria.
        transactions = self.transaction_repo.find_by_criteria(
            bank_id=bank_id,
            start_date=start_date,
            end_date=end_date
        )

        if not transactions:
            return {
                "period": f"{year}-{month:02d}",
                "total_income": 0.0,
                "total_expenses": 0.0,
                "category_breakdown": {},
                "transaction_count": 0
            }

        # 3. Aggregate totals
        income = 0.0
        expenses = 0.0
        categories = {}

        for txn in transactions:
            amount = txn.amount or 0.0
            if txn.transaction_type == "deposit":
                income += abs(amount)
            else:
                expenses += abs(amount)
                cat = txn.category or "Uncategorized"
                categories[cat] = categories.get(cat, 0.0) + abs(amount)

        return {
            "period": f"{year}-{month:02d}",
            "total_income": round(income, 2),
            "total_expenses": round(expenses, 2),
            "net_flow": round(income - expenses, 2),
            "category_breakdown": {k: round(v, 2) for k, v in categories.items()},
            "transaction_count": len(transactions),
            "transactions": transactions # Pass full list for table generation
        }
