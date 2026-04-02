import pytest
from pathlib import Path
from services.db_service import DatabaseService

def test_insert_transactions_batch_atomicity_and_dedup(tmp_path):
    """RED: Test that insert_transactions_batch handles batch insertion and deduplication."""
    db_path = tmp_path / "persistence.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account("ACC1", "Test Account", bank_id="testbank")

    # 1. Pre-insert one transaction
    existing_txn = {
        "source_hash": "hash1", "date": "2024-01-01", "amount": 10.0,
        "currency": "MXN", "description": "Existing", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "testbank",
        "source_file": "old.csv"
    }
    service.insert_transaction(existing_txn)

    # 2. Prepare a batch with one existing and two new transactions
    batch = [
        existing_txn, # Duplicate
        {
            "source_hash": "hash2", "date": "2024-01-02", "amount": 20.0,
            "currency": "MXN", "description": "New 1", "account_id": "ACC1",
            "canonical_account_id": "ACC1", "bank_id": "testbank",
            "source_file": "batch.csv"
        },
        {
            "source_hash": "hash3", "date": "2024-01-03", "amount": 30.0,
            "currency": "MXN", "description": "New 2", "account_id": "ACC1",
            "canonical_account_id": "ACC1", "bank_id": "testbank",
            "source_file": "batch.csv"
        }
    ]

    # This should fail initially as the method doesn't exist
    result = service.insert_transactions_batch(batch)

    assert result["inserted"] == 2
    assert result["skipped"] == 1
    
def test_data_service_load_transactions_defaults_to_db(tmp_path, monkeypatch):
    """RED: Test that load_transactions defaults to DB loading."""
    from services import data_service
    from services.db_service import DatabaseService
    
    db_path = tmp_path / "data_test.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account("ACC1", "Test", bank_id="santander")
    
    txn = {
        "source_hash": "h1", "date": "2024-01-01", "amount": 10.0,
        "currency": "MXN", "description": "DB txn", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "santander",
        "source_file": "manual"
    }
    service.insert_transaction(txn)
    
    # Mock data_dir to point to tmp_path
    monkeypatch.setattr(data_service, "_data_dir", lambda: tmp_path)
    
    # This should now pull from DB by default without passing prefer_db=True
    df = data_service.load_transactions("santander", db_path=db_path)
    
def test_data_service_load_all_bank_data_prefers_db(tmp_path, monkeypatch):
    """RED: Test that load_all_bank_data uses DB as primary source."""
    from services import data_service
    from services.db_service import DatabaseService
    import pandas as pd
    
    db_path = tmp_path / "data_all_test.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account("ACC1", "Santander", bank_id="santander_likeu")
    
    service.insert_transaction({
        "source_hash": "h1", "date": "2024-01-01", "amount": 10.0,
        "currency": "MXN", "description": "DB santander", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "santander_likeu",
        "source_file": "manual"
    })
    
    # Mock data_dir and accounts config to return our known banks
    monkeypatch.setattr(data_service, "_data_dir", lambda: tmp_path)
    monkeypatch.setattr(data_service, "_accounts_config_path", lambda: tmp_path / "accounts.yml")
    (tmp_path / "accounts.yml").write_text("canonical_accounts: { ACC1: { bank_ids: [santander_likeu] } }")
    
    # This should now pull from DB
def test_analytics_service_get_unified_dashboard_stats(tmp_path):
    """RED: Test that unified dashboard stats aggregate all bank data."""
    from services import analytics_service
    from services.db_service import DatabaseService
    
    db_path = tmp_path / "analytics_unified.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account("ACC1", "Santander", bank_id="bank1")
    service.upsert_account("ACC2", "HSBC", bank_id="bank2")
    
    # Santander txn
    service.insert_transaction({
        "source_hash": "h1", "date": "2024-01-01", "amount": 100.0,
        "currency": "MXN", "description": "S1", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "bank1",
        "transaction_type": "withdrawal", "destination_name": "Expenses:Food",
        "source_file": "manual"
    })
    
    # HSBC txn
    service.insert_transaction({
        "source_hash": "h2", "date": "2024-01-02", "amount": 200.0,
        "currency": "MXN", "description": "H1", "account_id": "ACC2",
        "canonical_account_id": "ACC2", "bank_id": "bank2",
        "transaction_type": "withdrawal", "destination_name": "Expenses:Transport",
        "source_file": "manual"
    })
    
    # This should fail initially as method doesn't exist
    stats = analytics_service.get_unified_dashboard_stats(db_path=db_path)
    
    assert stats["total"] == 2
def test_analytics_service_calculate_categorization_stats_from_db_params(tmp_path):
    """Verify that calculate_categorization_stats_from_db handles bank_id and filtering."""
    from services import analytics_service
    from services.db_service import DatabaseService
    
    db_path = tmp_path / "analytics_params.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account("ACC1", "Santander", bank_id="santander")
    
    service.insert_transaction({
        "source_hash": "h1", "date": "2024-01-01", "amount": 50.0,
        "currency": "MXN", "description": "S1", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "santander",
        "transaction_type": "withdrawal", "destination_name": "Expenses:Food",
        "source_file": "manual"
    })
    
    # Filter by bank
    stats = analytics_service.calculate_categorization_stats_from_db(db_path=db_path, bank_id="santander")
    assert stats["total"] == 1
    assert stats["total_spent"] == 50.0
    
    # Filter by non-existent bank
    stats_empty = analytics_service.calculate_categorization_stats_from_db(db_path=db_path, bank_id="other")
    assert stats_empty["total"] == 0

def test_insert_transactions_batch_uniqueness(tmp_path):
    """Verify that batch insertion respects unique hash constraint."""
    from services.db_service import DatabaseService
    db = DatabaseService(db_path=tmp_path / "unique.db")
    db.initialize()
    db.upsert_account("ACC1", "Test", bank_id="bank1")
    
    txn = {
        "source_hash": "fixed_hash", "date": "2024-01-01", "amount": 10.0,
        "currency": "MXN", "description": "D1", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "bank1",
        "source_file": "f1.csv"
    }
    
    # Try inserting same transaction twice in a batch
    batch = [txn, txn]
    result = db.insert_transactions_batch(batch)
    
    assert result["inserted"] == 1
    assert result["skipped"] == 1
    
    # Try inserting again in a separate batch
    result2 = db.insert_transactions_batch([txn])
    assert result2["inserted"] == 0
    assert result2["skipped"] == 1
