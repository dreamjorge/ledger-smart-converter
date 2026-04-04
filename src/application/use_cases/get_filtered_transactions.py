from datetime import date
from typing import List, Optional, Dict, Any
from application.ports.transaction_repository import TransactionRepository
from domain.transaction import CanonicalTransaction

class GetFilteredTransactions:
    """
    Use case to fetch transactions based on UI-provided filters (bank, dates, tags).
    """
    def __init__(self, repository: TransactionRepository):
        self.repository = repository

    def execute(
        self, 
        bank_id: Optional[str] = None, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        period: Optional[str] = None
    ) -> List[CanonicalTransaction]:
        tags = [f"period:{period}"] if period else []
        return self.repository.find_by_criteria(
            bank_id=bank_id,
            start_date=start_date,
            end_date=end_date,
            tags=tags
        )
