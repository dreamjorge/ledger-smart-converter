from pathlib import Path

import yaml

from services import rule_service as rs


def _seed_rules(path: Path) -> None:
    data = {
        "rules": [
            {
                "name": "Groceries",
                "any_regex": ["walmart"],
                "set": {"expense": "Expenses:Food:Groceries", "tags": ["bucket:groceries"]},
            }
        ]
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_stage_and_merge_rule_creates_backup(tmp_path: Path):
    rules_path = tmp_path / "rules.yml"
    pending_path = tmp_path / "rules.pending.yml"
    backup_dir = tmp_path / "backups"
    _seed_rules(rules_path)

    ok_stage, stage = rs.stage_rule_change(
        rules_path=rules_path,
        pending_path=pending_path,
        merchant_name="spotify",
        regex_pattern="spotify",
        expense_account="Expenses:Entertainment:Subscriptions",
        bucket_tag="subscriptions",
    )
    assert ok_stage is True
    assert stage["status"] == "staged"
    assert pending_path.exists()

    ok_merge, merge = rs.merge_pending_rules(rules_path, pending_path, backup_dir)
    assert ok_merge is True
    assert merge["status"] == "merged"
    assert merge["merged_count"] == 1
    assert Path(merge["backup_path"]).exists()
    assert pending_path.exists() is False


def test_stage_detects_conflict_on_existing_regex(tmp_path: Path):
    rules_path = tmp_path / "rules.yml"
    pending_path = tmp_path / "rules.pending.yml"
    _seed_rules(rules_path)
    ok, result = rs.stage_rule_change(
        rules_path=rules_path,
        pending_path=pending_path,
        merchant_name="walmart_fix",
        regex_pattern="walmart",
        expense_account="Expenses:Food:Groceries",
        bucket_tag="groceries",
    )
    assert ok is False
    assert result["status"] == "conflict"
