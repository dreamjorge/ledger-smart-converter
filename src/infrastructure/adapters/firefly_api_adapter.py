import requests
from typing import List, Dict, Any, Optional
from application.ports.firefly_sync_port import FireflySyncPort
from domain.transaction import CanonicalTransaction
from logging_config import get_logger

logger = get_logger("firefly_adapter")

class FireflyApiAdapter(FireflySyncPort):
    def __init__(self, api_url: str, personal_token: str):
        self.api_url = api_url.rstrip('/')
        if not self.api_url.endswith('/api/v1'):
            self.api_url = f"{self.api_url}/api/v1"
        
        self.headers = {
            "Authorization": f"Bearer {personal_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def verify_connection(self) -> bool:
        """Verify the API token is valid by calling the 'about' endpoint."""
        try:
            response = requests.get(f"{self.api_url}/about", headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Firefly III: {e}")
            return False

    def push_transactions(self, transactions: List[CanonicalTransaction]) -> Dict[str, Any]:
        """
        Push transactions to Firefly III in batches.
        Returns synced hashes and errors.
        """
        synced_hashes = []
        errors = []

        for txn in transactions:
            try:
                payload = self._map_to_firefly_json(txn)
                response = requests.post(
                    f"{self.api_url}/transactions", 
                    json=payload, 
                    headers=self.headers, 
                    timeout=15
                )

                if response.status_code in (200, 201):
                    synced_hashes.append(txn.id)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Error syncing transaction {txn.id}: {error_msg}")
                    errors.append({"hash": txn.id, "error": error_msg})
            except Exception as e:
                logger.error(f"Exception syncing transaction {txn.id}: {e}")
                errors.append({"hash": txn.id, "error": str(e)})

        return {
            "synced_hashes": synced_hashes,
            "errors": errors
        }

    def get_account_id(self, name: str) -> Optional[int]:
        """Retrieve Firefly ID for an account name (not strictly needed if using names in push)."""
        # For now we use names to simplify, as Firefly supports auto-creation by name.
        return None

    def _map_to_firefly_json(self, txn: CanonicalTransaction) -> Dict[str, Any]:
        """Translate domain object to Firefly III API payload."""
        # Firefly expects a 'transactions' array even for single entries
        return {
            "error_if_duplicate_hash": True,
            "transactions": [{
                "type": txn.transaction_type,
                "date": txn.date,
                "amount": f"{abs(txn.amount):.2f}" if txn.amount is not None else "0.00",
                "description": txn.description,
                "source_name": txn.source_name or txn.account_id,
                "destination_name": txn.destination_name or "",
                "category_name": txn.category or "",
                "tags": txn.tags.split(',') if txn.tags else [],
                "external_id": txn.id,
                "notes": txn.notes or ""
            }]
        }
