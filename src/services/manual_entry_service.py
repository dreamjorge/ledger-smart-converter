# -*- coding: utf-8 -*-
"""Service for manual single-transaction entry.

Provides helpers to:
- Load category and account options from config files.
- Validate and persist a single manually-entered transaction to the database.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from services.contracts import ManualEntryResult, TransactionInsertRow
from services.rules_config_service import (
    load_bank_display_names,
    load_expense_categories,
)

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
    return load_expense_categories(rules_path)


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
    if rules_path:
        bank_names = load_bank_display_names(rules_path)

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


def _build_manual_transaction_row(
    *,
    source_hash: str,
    date: str,
    description: str,
    amount: float,
    bank_id: str,
    account_id: str,
    canonical_account_id: str,
    transaction_type: str,
    category: str,
) -> TransactionInsertRow:
    return {
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
        "tags": "manual:entry",
    }


from application.ports.transaction_repository import TransactionRepository
from application.use_cases.submit_manual_transaction import SubmitManualTransaction
from infrastructure.adapters.sqlite_transaction_repository import SqliteTransactionRepository

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
) -> ManualEntryResult:
    """Validate and persist a single manually-entered transaction.

    This service function now acts as an adapter/bridge to the Clean Architecture 
    implementation, preserving the original signature for backward compatibility.
    """
    # 1. Create the domain object (CanonicalTransaction)
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

    # 2. Basic validation (still using the existing validator for now)
    errors = validate_transaction(txn)
    if errors:
        return False, errors

    # 3. Initialize Infrastructure and Application layers
    db_service = DatabaseService(db_path=db_path)
    # We ensure DB is initialized here for safety, though the repository could do it.
    db_service.initialize() 
    
    repository = SqliteTransactionRepository(db_service)
    use_case = SubmitManualTransaction(repository)

    # 4. Execute the Use Case
    # Note: The use case currently returns a boolean. 
    # For now, we perform the insertion manually if use case says OK, 
    # OR we update the repository/use case to handle the full task.
    
    # Let's improve the repository and use case to handle the insert_transaction call 
    # so the service is truly a thin wrapper.
    
    # Check for existence via use case logic
    if repository.exists(txn.id):
         return False, ["duplicate"]

    # Build the row (Infrastructure detail)
    source_hash = txn.id # Using the domain ID as source_hash
    txn_dict = _build_manual_transaction_row(
        source_hash=source_hash,
        date=date,
        description=description,
        amount=amount,
        bank_id=bank_id,
        account_id=account_id,
        canonical_account_id=canonical_account_id,
        transaction_type=transaction_type,
        category=category,
    )

    # Actually we should let the repository handle the mapping from Domain -> DB Row.
    # For this first iteration, we just delegate the final save.
    success = repository.save_manual(txn_dict, user_id=user_id)
    
    if success:
        return True, []
    else:
        return False, ["persistence_error"]
