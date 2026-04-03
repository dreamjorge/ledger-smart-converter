from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_rules_config(rules_path: Path) -> Dict[str, Any]:
    """Load the canonical rules config, returning an empty mapping when absent."""
    if not rules_path.exists():
        return {}
    with open(rules_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_expense_categories(rules_path: Path) -> List[str]:
    """Return sorted canonical expense categories from the shared rules contract."""
    config = load_rules_config(rules_path)

    expenses = set()
    fallback = config.get("defaults", {}).get("fallback_expense")
    if fallback:
        expenses.add(fallback)

    for rule in config.get("rules", []):
        expense = (rule.get("set") or {}).get("expense")
        if expense:
            expenses.add(expense)

    return sorted(expenses)


def load_bank_display_names(rules_path: Path) -> Dict[str, str]:
    """Return bank display names keyed by bank id from the shared rules contract."""
    config = load_rules_config(rules_path)
    bank_names: Dict[str, str] = {}

    for bank_id, bank_cfg in config.get("banks", {}).items():
        bank_names[bank_id] = bank_cfg.get("display_name", bank_id)

    return bank_names
