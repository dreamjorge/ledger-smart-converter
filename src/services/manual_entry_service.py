# -*- coding: utf-8 -*-
"""Service for manual single-transaction entry.

Provides helpers to:
- Load category and account options from config files.
- Validate and persist a single manually-entered transaction to the database.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Maps Firefly III expense account paths → translation key suffix
# Used by UIs to show friendly names instead of raw paths.
CATEGORY_KEY_MAP: Dict[str, str] = {
    "Expenses:Entertainment:Cinema": "cat_cinema",
    "Expenses:Entertainment:DigitalServices": "cat_digitalservices",
    "Expenses:Fees:Bank": "cat_bank",
    "Expenses:Fees:Government": "cat_government",
    "Expenses:Food:Groceries": "cat_groceries",
    "Expenses:Food:Restaurants": "cat_restaurants",
    "Expenses:Health:Pharmacy": "cat_pharmacy",
    "Expenses:Other:Uncategorized": "cat_uncategorized",
    "Expenses:Shopping:General": "cat_general",
    "Expenses:Transport:Fuel": "cat_fuel",
    "Expenses:Transport:Maintenance": "cat_maintenance",
    "Expenses:Transport:RideShare": "cat_rideshare",
}


def get_category_label(expense_path: str, lang: str = "es") -> str:
    """Return a human-friendly category label for *expense_path*.

    Falls back to the raw path if no mapping exists.
    """
    from translations import TRANSLATIONS

    key = CATEGORY_KEY_MAP.get(expense_path)
    if key:
        return TRANSLATIONS.get(lang, {}).get(key, expense_path)
    return expense_path


from domain.transaction import CanonicalTransaction
from services.db_service import DatabaseService
from validation import validate_transaction


def load_categories_from_rules(rules_path: Path) -> List[str]:
    """Return a sorted list of unique expense account strings from rules.yml.

    Reads the ``defaults.fallback_expense`` value plus every ``rules[*].set.expense``
    entry and returns them deduplicated and sorted.
    """
    if not rules_path.exists():
        return []
    with open(rules_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    expenses: set = set()
    fallback = cfg.get("defaults", {}).get("fallback_expense")
    if fallback:
        expenses.add(fallback)
    for rule in cfg.get("rules", []):
        exp = (rule.get("set") or {}).get("expense")
        if exp:
            expenses.add(exp)
    return sorted(expenses)


def load_accounts_from_config(
    accounts_path: Path,
    rules_path: Optional[Path] = None,
) -> Dict[str, str]:
    """Return {canonical_id: display_label} for all canonical_accounts.

    The display label is built from the first account_id string in accounts.yml.
    If rules_path is provided, the bank display_name from rules.yml is appended
    for clarity (e.g. "Liabilities:CC:Santander LikeU (Santander LikeU)").
    """
    if not accounts_path.exists():
        return {}
    with open(accounts_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    bank_names: Dict[str, str] = {}
    if rules_path and rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            rules_cfg = yaml.safe_load(f) or {}
        for bank_id, bank_cfg in rules_cfg.get("banks", {}).items():
            bank_names[bank_id] = bank_cfg.get("display_name", bank_id)

    result: Dict[str, str] = {}
    for canonical_id, acc_cfg in cfg.get("canonical_accounts", {}).items():
        account_ids = acc_cfg.get("account_ids", [])
        label = account_ids[0] if account_ids else canonical_id
        # Append bank name if available
        bank_ids = acc_cfg.get("bank_ids", [])
        if bank_ids and bank_ids[0] in bank_names:
            label = f"{label} ({bank_names[bank_ids[0]]})"
        result[canonical_id] = label
    return result


def submit_manual_transaction(
    *,
    date: str,
    description: str,
    amount: float,
    bank_id: str,
    account_id: str,
    canonical_account_id: str,
    transaction_type: str,
    category: str,
    db_path: Optional[Path] = None,
    user_id: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Validate and persist a single manually-entered transaction.

    Args:
        date: ISO date string (YYYY-MM-DD).
        description: Free-text description of the transaction.
        amount: Transaction amount (positive = expense/withdrawal).
        bank_id: Bank identifier (e.g. "santander_likeu").
        account_id: Display account ID (e.g. "Liabilities:CC:Santander LikeU").
        canonical_account_id: Canonical account key (e.g. "cc:santander_likeu").
        transaction_type: One of "withdrawal", "transfer", "deposit".
        category: Expense account string (e.g. "Expenses:Food:Groceries").
        db_path: Optional path to the SQLite database. Uses settings default if None.

    Returns:
        (True, []) on successful insert.
        (False, ["duplicate"]) if the transaction already exists.
        (False, [error_code, ...]) on validation failure.
    """
    txn = CanonicalTransaction(
        date=date,
        description=description,
        amount=amount,
        bank_id=bank_id,
        account_id=account_id,
        canonical_account_id=canonical_account_id,
        raw_description=description,
        normalized_description=description,
        source="manual",
    )

    errors = validate_transaction(txn)
    if errors:
        return False, errors

    db = DatabaseService(db_path=db_path)
    db.initialize()
    source_hash = db.build_source_hash(
        bank_id,
        "manual",
        date,
        amount,
        description,
        canonical_account_id=canonical_account_id,
    )

    if db.transaction_exists(source_hash):
        return False, ["duplicate"]

    txn_dict: Dict[str, Any] = {
        "source_hash": source_hash,
        "date": date,
        "amount": amount,
        "currency": "MXN",
        "description": description,
        "raw_description": description,
        "normalized_description": description,
        "account_id": account_id,
        "canonical_account_id": canonical_account_id,
        "bank_id": bank_id,
        "transaction_type": transaction_type,
        "category": category,
        "source_file": "manual",
        "tags": f"manual:entry",
    }

    db.insert_transaction(txn_dict, user_id=user_id)
    return True, []
