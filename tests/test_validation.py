from domain.transaction import CanonicalTransaction
from validation import validate_tags, validate_transaction


def test_validate_transaction_happy_path():
    txn = CanonicalTransaction(
        date="2026-02-01",
        description="WAL MART QUERETARO",
        amount=-250.00,
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
    )
    assert validate_transaction(txn) == []


def test_validate_transaction_invalid_date():
    txn = CanonicalTransaction(
        date="01/02/2026",
        description="TEST",
        amount=100.0,
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
    )
    assert "invalid_date" in validate_transaction(txn)


def test_validate_tags_rejects_spaces():
    errors = validate_tags(["bucket:groceries", "bad tag"])
    assert errors == ["invalid_tag:bad tag"]
