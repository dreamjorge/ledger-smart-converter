from pathlib import Path

import services.rule_service as rule_service
from ui.flet_ui import rule_hub_view


def test_load_canonical_rule_hub_categories_reads_rules_taxonomy(tmp_path):
    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        """
defaults:
  fallback_expense: Expenses:Other:Uncategorized
rules:
  - set:
      expense: Expenses:Entertainment:DigitalServices
  - set:
      expense: Expenses:Food:Groceries
""".strip(),
        encoding="utf-8",
    )

    categories = rule_hub_view.load_canonical_rule_hub_categories(rules_path)

    assert "Expenses:Entertainment:DigitalServices" in categories
    assert "Expenses:Services:Digital" not in categories


def test_merge_pending_rules_with_retrain_reports_training_result(
    tmp_path, monkeypatch
):
    rules_path = tmp_path / "rules.yml"
    pending_path = tmp_path / "rules.pending.yml"
    backup_dir = tmp_path / "backups"
    rules_path.write_text("rules: []\n", encoding="utf-8")
    pending_path.write_text(
        """
pending_rules:
  - name: UserCorrection:Netflix
    any_regex:
      - netflix
    set:
      expense: Expenses:Entertainment:DigitalServices
      tags: [bucket:subs]
""".strip(),
        encoding="utf-8",
    )

    trained = {"called": False}

    def fake_train():
        trained["called"] = True

    result = rule_hub_view.merge_pending_rules_with_retrain(
        rules_path=rules_path,
        pending_path=pending_path,
        backup_dir=backup_dir,
        merge_rules=rule_service.merge_pending_rules,
        retrain_model=fake_train,
    )

    assert result["merge_success"] is True
    assert result["retrained"] is True
    assert trained["called"] is True
