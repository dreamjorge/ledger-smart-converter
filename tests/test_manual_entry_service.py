from pathlib import Path

from services.db_service import DatabaseService
from services.manual_entry_service import (
    get_category_label,
    load_accounts_from_config,
    load_categories_from_rules,
    submit_manual_transaction,
)
from services.user_service import create_user


def test_load_categories_from_rules_returns_sorted_unique_values(tmp_path):
    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        """
defaults:
  fallback_expense: Expenses:Other:Uncategorized
rules:
  - set:
      expense: Expenses:Food:Groceries
  - set:
      expense: Expenses:Food:Restaurants
  - set:
      expense: Expenses:Food:Groceries
""".strip(),
        encoding="utf-8",
    )

    assert load_categories_from_rules(rules_path) == [
        "Expenses:Food:Groceries",
        "Expenses:Food:Restaurants",
        "Expenses:Other:Uncategorized",
    ]


def test_load_accounts_from_config_includes_bank_display_names(tmp_path):
    accounts_path = tmp_path / "accounts.yml"
    rules_path = tmp_path / "rules.yml"
    accounts_path.write_text(
        """
canonical_accounts:
  cc:santander_likeu:
    account_ids:
      - Liabilities:CC:Santander LikeU
    bank_ids:
      - santander_likeu
  cash:shared:
    account_ids:
      - Assets:Cash:Wallet
""".strip(),
        encoding="utf-8",
    )
    rules_path.write_text(
        """
banks:
  santander_likeu:
    display_name: Santander LikeU
""".strip(),
        encoding="utf-8",
    )

    assert load_accounts_from_config(accounts_path, rules_path) == {
        "cc:santander_likeu": "Liabilities:CC:Santander LikeU (Santander LikeU)",
        "cash:shared": "Assets:Cash:Wallet",
    }


def test_get_category_label_uses_translation_key_and_fallback():
    assert get_category_label("Expenses:Transport:Fuel", "es") == "Gasolina"
    assert (
        get_category_label("Expenses:Unknown:Other", "es") == "Expenses:Unknown:Other"
    )


def test_submit_manual_transaction_inserts_transaction_and_user(tmp_path):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    create_user(db, "maria", "Maria")
    db.upsert_account(
        account_id="cc:santander_likeu",
        display_name="Santander LikeU",
        bank_id="santander_likeu",
    )

    ok, errors = submit_manual_transaction(
        date="2026-03-15",
        description="Supermercado",
        amount=123.45,
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
        canonical_account_id="cc:santander_likeu",
        transaction_type="withdrawal",
        category="Expenses:Food:Groceries",
        db_path=db.db_path,
        user_id="maria",
    )

    row = db.fetch_one(
        "SELECT * FROM transactions WHERE description = ?", ("Supermercado",)
    )

    assert ok is True
    assert errors == []
    assert row["user_id"] == "maria"
    assert row["category"] == "Expenses:Food:Groceries"
    assert row["source_file"] == "manual"


def test_submit_manual_transaction_rejects_duplicates(tmp_path):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account(
        account_id="cc:santander_likeu",
        display_name="Santander LikeU",
        bank_id="santander_likeu",
    )

    first = submit_manual_transaction(
        date="2026-03-15",
        description="Cafe",
        amount=89.5,
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
        canonical_account_id="cc:santander_likeu",
        transaction_type="withdrawal",
        category="Expenses:Food:Restaurants",
        db_path=db.db_path,
    )
    second = submit_manual_transaction(
        date="2026-03-15",
        description="Cafe",
        amount=89.5,
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
        canonical_account_id="cc:santander_likeu",
        transaction_type="withdrawal",
        category="Expenses:Food:Restaurants",
        db_path=db.db_path,
    )

    assert first == (True, [])
    assert second == (False, ["duplicate"])


def test_submit_manual_transaction_returns_validation_errors(tmp_path):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()

    ok, errors = submit_manual_transaction(
        date="2026/03/15",
        description="",
        amount=12.0,
        bank_id="",
        account_id="",
        canonical_account_id="",
        transaction_type="withdrawal",
        category="Expenses:Other:Uncategorized",
        db_path=db.db_path,
    )

    assert ok is False
    assert errors == [
        "invalid_date",
        "missing_description",
        "missing_bank_id",
        "missing_account_id",
        "missing_canonical_account_id",
    ]
