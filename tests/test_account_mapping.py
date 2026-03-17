from pathlib import Path

from account_mapping import resolve_canonical_account_id


def test_resolve_canonical_account_from_config(tmp_path):
    accounts_path = tmp_path / "accounts.yml"
    accounts_path.write_text(
        """
version: 1
canonical_accounts:
  cc:santander_likeu:
    bank_ids: [santander_likeu, santander]
    account_ids: ["Liabilities:CC:Santander LikeU"]
""".strip(),
        encoding="utf-8",
    )

    canonical = resolve_canonical_account_id(
        bank_id="santander_likeu",
        account_id="Liabilities:CC:Santander LikeU",
        accounts_path=accounts_path,
    )
    assert canonical == "cc:santander_likeu"


def test_resolve_canonical_account_falls_back_to_bank_id(tmp_path):
    accounts_path = tmp_path / "accounts.yml"
    accounts_path.write_text("version: 1\ncanonical_accounts: {}\n", encoding="utf-8")

    canonical = resolve_canonical_account_id(
        bank_id="new_bank",
        account_id="Liabilities:CC:Custom",
        accounts_path=accounts_path,
    )
    assert canonical == "cc:new_bank"


def test_resolve_canonical_account_uses_default_when_bank_id_missing(tmp_path):
    accounts_path = tmp_path / "accounts.yml"
    accounts_path.write_text("version: 1\ncanonical_accounts: {}\n", encoding="utf-8")

    canonical = resolve_canonical_account_id(
        bank_id="",
        account_id="Liabilities:CC:Unknown",
        accounts_path=accounts_path,
    )
    assert canonical == "cc:unknown"
