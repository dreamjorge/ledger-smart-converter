from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Dict, Any
from domain.transaction import CanonicalTransaction

class TransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: CanonicalTransaction) -> bool:
        """Persists a transaction in the data store."""
        pass

    @abstractmethod
    def exists(self, transaction_hash: str) -> bool:
        """Verifies if a transaction already exists based on its hash."""
        pass

    @abstractmethod
    def fetch_all(self) -> List[CanonicalTransaction]:
        """Retrieves all persisted transactions."""
        pass

    @abstractmethod
    def find_by_criteria(
        self, 
        bank_id: Optional[str] = None, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None, 
        tags: List[str] = []
    ) -> List[CanonicalTransaction]:
        """
        Retrieves transactions based on specific criteria.
        
        Args:
            bank_id: Filter by original bank identifier.
            start_date: Filter transactions on or after this date.
            end_date: Filter transactions on or before this date.
            tags: List of tags (e.g., 'period:2024-01') that MUST be present.
            
        Returns:
            List of CanonicalTransaction matching ALL criteria.
        """
        pass

    @abstractmethod
    def save_all(self, transactions: List[CanonicalTransaction]) -> Dict[str, Any]:
        """
        Persists multiple transactions in the data store efficiently.
        
        Returns:
            Dict containing counts of 'inserted', 'skipped_duplicates', 'errors'.
        """
        pass
