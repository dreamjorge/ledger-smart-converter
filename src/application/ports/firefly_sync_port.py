from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.transaction import CanonicalTransaction

class FireflySyncPort(ABC):
    @abstractmethod
    def push_transactions(self, transactions: List[CanonicalTransaction]) -> Dict[str, Any]:
        """
        Push a list of transactions to Firefly III.
        Returns a dictionary with 'synced_count' and 'errors'.
        """
        pass

    @abstractmethod
    def verify_connection(self) -> bool:
        """
        Check if the connection to the Firefly III API is valid.
        """
        pass

    @abstractmethod
    def get_account_id(self, name: str) -> Optional[int]:
        """
        Retrieve the internal Firefly ID for an account name.
        """
        pass
