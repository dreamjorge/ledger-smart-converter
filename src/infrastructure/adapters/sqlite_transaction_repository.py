from datetime import date
from typing import List, Optional, Dict, Any
import pandas as pd
from application.ports.transaction_repository import TransactionRepository
from domain.transaction import CanonicalTransaction
from services.db_service import DatabaseService

class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def save(self, transaction: CanonicalTransaction) -> bool:
        """Persists a transaction in SQLite via DatabaseService."""
        # Convert Domain Object to Dict for DatabaseService
        txn_dict = {
            "date": transaction.date,
            "description": transaction.description,
            "amount": transaction.amount,
            "bank_id": transaction.bank_id,
            "account_id": transaction.account_id,
            "canonical_account_id": transaction.canonical_account_id,
            "transaction_type": transaction.transaction_type,
            "category": transaction.category,
            "notes": transaction.notes,
            "tags": transaction.tags,
            "source": transaction.source,
            "raw_description": transaction.raw_description,
            "normalized_description": transaction.normalized_description,
            "source_hash": transaction.id,
        }
        return self.db_service.insert_transaction(txn_dict)

    def exists(self, transaction_hash: str) -> bool:
        """Verifies if the hash already exists in the DB."""
        return self.db_service.transaction_exists(transaction_hash)

    def fetch_all(self) -> List[CanonicalTransaction]:
        """Retrieves all transactions from the DB mapped to Domain objects."""
        rows = self.db_service.fetch_all("SELECT * FROM transactions ORDER BY date")
        return [self._map_row_to_domain(row) for row in rows]

    def find_by_criteria(
        self, 
        bank_id: Optional[str] = None, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None, 
        tags: List[str] = []
    ) -> List[CanonicalTransaction]:
        """
        Retrieves transactions based on specific criteria using dynamic SQL.
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if bank_id:
            query += " AND bank_id = ?"
            params.append(bank_id)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date.strftime("%Y-%m-%d"))
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date.strftime("%Y-%m-%d"))
        
        for tag in tags:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        
        query += " ORDER BY date"
        
        rows = self.db_service.fetch_all(query, tuple(params))
        return [self._map_row_to_domain(row) for row in rows]

    def save_all(self, transactions: List[CanonicalTransaction], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Persists multiple transactions in batch mode."""
        txn_rows = [self._map_domain_to_dict(t, user_id=user_id) for t in transactions]
        results = self.db_service.insert_transactions_batch(txn_rows)
        return {
            "inserted": results.get("inserted", 0),
            "skipped_duplicates": results.get("skipped", 0),
            "errors": 0  # DatabaseService handles errors internally or skips them
        }

    def save_manual(self, transaction: Any, **kwargs) -> bool:
        """
        Save a single manual transaction.
        Maintained for backward compatibility with existing legacy tests.
        """
        from domain.transaction import CanonicalTransaction
        
        if isinstance(transaction, dict):
            # Convert dict to CanonicalTransaction for legacy callers
            transaction = CanonicalTransaction(
                date=transaction.get("date"),
                description=transaction.get("description"),
                amount=float(transaction.get("amount", 0)),
                bank_id=transaction.get("bank_id"),
                account_id=transaction.get("account_id"),
                canonical_account_id=transaction.get("canonical_account_id"),
                transaction_type=transaction.get("transaction_type", "withdrawal"),
                category=transaction.get("category"),
                notes=transaction.get("notes"),
                tags=transaction.get("tags", ""),
                destination_name=transaction.get("destination_name"),
                source=transaction.get("source", "manual"),
                raw_description=transaction.get("raw_description", transaction.get("description", "")),
                normalized_description=transaction.get("normalized_description", transaction.get("description", ""))
            )
            
        user_id = kwargs.get("user_id")
        results = self.save_all([transaction], user_id=user_id)
        return results.get("inserted", 0) > 0

    def _map_domain_to_dict(self, transaction: CanonicalTransaction, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Helper to map a CanonicalTransaction domain object to a database dictionary."""
        row = {
            "date": transaction.date,
            "description": transaction.description,
            "amount": transaction.amount,
            "bank_id": transaction.bank_id,
            "account_id": transaction.account_id,
            "canonical_account_id": transaction.canonical_account_id,
            "transaction_type": transaction.transaction_type,
            "category": transaction.category,
            "notes": transaction.notes,
            "tags": transaction.tags,
            "destination_name": transaction.destination_name,
            "source": transaction.source,
            "source_file": transaction.source, # Map source to source_file for DatabaseService
            "raw_description": transaction.raw_description,
            "normalized_description": transaction.normalized_description,
            "source_hash": transaction.id,
        }
        if user_id:
            row["user_id"] = user_id
        return row

    def _map_row_to_domain(self, row: Dict[str, Any]) -> CanonicalTransaction:
        """Helper to map a DB row to a CanonicalTransaction domain object."""
        return CanonicalTransaction(
            date=row["date"],
            description=row["description"],
            amount=row["amount"],
            bank_id=row["bank_id"],
            account_id=row["account_id"],
            canonical_account_id=row.get("canonical_account_id"),
            transaction_type=row.get("transaction_type", "withdrawal"),
            category=row.get("category"),
            notes=row.get("notes"),
            tags=row.get("tags"),
            destination_name=row.get("destination_name"),
            source=row.get("source"),
            raw_description=row.get("raw_description"),
            normalized_description=row.get("normalized_description")
        )
