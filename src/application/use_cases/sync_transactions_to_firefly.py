from typing import List, Dict, Any, Optional
from application.ports.transaction_repository import TransactionRepository
from application.ports.firefly_sync_port import FireflySyncPort
from domain.transaction import CanonicalTransaction

class SyncTransactionsToFirefly:
    def __init__(
        self, 
        transaction_repo: TransactionRepository, 
        firefly_sync_port: FireflySyncPort
    ):
        self.transaction_repo = transaction_repo
        self.firefly_sync_port = firefly_sync_port

    def execute(self, bank_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the sync process for unsynced transactions.
        Optional bank_id filter.
        """
        # 1. Get unsynced transactions
        # Note: We filter by bank_id in memory for simplicity if the port doesn't support it directly
        all_unsynced = self.transaction_repo.get_unsynced()
        
        if bank_id:
            to_sync = [t for t in all_unsynced if t.bank_id == bank_id]
        else:
            to_sync = all_unsynced

        if not to_sync:
            return {
                "status": "success",
                "synced_count": 0,
                "message": "No new transactions to sync."
            }

        # 2. Push to Firefly
        results = self.firefly_sync_port.push_transactions(to_sync)
        
        # 3. Mark as synced in repository
        # We only mark those that were successfully pushed
        synced_hashes = results.get("synced_hashes", [])
        if synced_hashes:
            self.transaction_repo.mark_as_synced(synced_hashes)

        return {
            "status": "success" if not results.get("errors") else "partial_success",
            "synced_count": len(synced_hashes),
            "error_count": len(results.get("errors", [])),
            "details": results
        }
