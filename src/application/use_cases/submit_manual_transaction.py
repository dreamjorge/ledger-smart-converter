from application.ports.transaction_repository import TransactionRepository
from domain.transaction import CanonicalTransaction

class SubmitManualTransaction:
    def __init__(self, repository: TransactionRepository):
        self.repository = repository

    def execute(self, transaction: CanonicalTransaction) -> bool:
        """
        Orchestrates the saving operation of a manual transaction.
        
        1. Verifies that the hash does not exist.
        2. Persists the transaction.
        """
        if self.repository.exists(transaction.id):
            return False # Already exists, avoiding duplicates
            
        return self.repository.save(transaction)
