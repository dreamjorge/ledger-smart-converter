from pathlib import Path

import yaml

from services import rule_service as rs
from services.db_service import DatabaseService


def _seed_rules(path: Path) -> None:
    path.write_text(
        yaml.safe_dump({"rules": []}, sort_keys=False),
        encoding="utf-8",
    )


def test_stage_and_merge_write_audit_events(tmp_path):
    rules_path = tmp_path / "rules.yml"
    pending_path = tmp_path / "rules.pending.yml"
    backup_dir = tmp_path / "backups"
    db_path = tmp_path / "ledger.db"
    _seed_rules(rules_path)

    db = DatabaseService(db_path=db_path)
    db.initialize()

    ok_stage, _ = rs.stage_rule_change(
        rules_path=rules_path,
        pending_path=pending_path,
        merchant_name="spotify",
        regex_pattern="spotify",
        expense_account="Expenses:Entertainment:Subscriptions",
        bucket_tag="subscriptions",
        db_path=db_path,
    )
    assert ok_stage is True

    ok_merge, _ = rs.merge_pending_rules(
        rules_path=rules_path,
        pending_path=pending_path,
        backup_dir=backup_dir,
        db_path=db_path,
    )
    assert ok_merge is True

    events = db.fetch_all("SELECT event_type FROM audit_events ORDER BY id")
    event_types = [e["event_type"] for e in events]
    assert "rule_staged" in event_types
    assert "rules_merged" in event_types


def test_record_recategorization_event(tmp_path):
    db_path = tmp_path / "ledger.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()

    rs.record_recategorization_event(
        db_path=db_path,
        transaction_source_hash="hash123",
        old_category="Food",
        new_category="Entertainment",
        reason="user correction",
    )

    row = db.fetch_one("SELECT event_type, entity_id FROM audit_events WHERE entity_id = ?", ("hash123",))
    assert row["event_type"] == "recategorization"
    assert row["entity_id"] == "hash123"
