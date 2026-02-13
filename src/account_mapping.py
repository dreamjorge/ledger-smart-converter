from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import yaml

from settings import load_settings


def _normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


@lru_cache(maxsize=8)
def _load_accounts_config(accounts_path: Path) -> Dict:
    if not accounts_path.exists():
        return {}
    return yaml.safe_load(accounts_path.read_text(encoding="utf-8")) or {}


def resolve_canonical_account_id(
    bank_id: str,
    account_id: str,
    accounts_path: Optional[Path] = None,
) -> str:
    settings = load_settings()
    cfg_path = accounts_path or (settings.config_dir / "accounts.yml")
    cfg = _load_accounts_config(cfg_path)

    bank_norm = _normalize(bank_id)
    account_norm = _normalize(account_id)
    canonical_accounts = cfg.get("canonical_accounts", {})

    for canonical_id, entry in canonical_accounts.items():
        bank_ids = [_normalize(v) for v in entry.get("bank_ids", [])]
        account_ids = [_normalize(v) for v in entry.get("account_ids", [])]
        if bank_norm in bank_ids and (not account_ids or account_norm in account_ids):
            return canonical_id

    if bank_norm:
        return f"cc:{bank_norm}"
    return "cc:unknown"
