from pathlib import Path

import yaml
import pytest

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


# ===========================
# Integration Tests (Existing)
# ===========================

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


# ===========================
# Unit Tests for Helper Functions
# ===========================

class TestLoadYaml:
    """Test _load_yaml helper function."""

    def test_loads_valid_yaml_file(self, tmp_path):
        """Test loading valid YAML file."""
        yaml_path = tmp_path / "test.yml"
        data = {"key": "value", "number": 42}
        yaml_path.write_text(yaml.safe_dump(data), encoding="utf-8")

        loaded = rs._load_yaml(yaml_path)
        assert loaded["key"] == "value"
        assert loaded["number"] == 42

    def test_returns_empty_dict_when_file_not_exists(self, tmp_path):
        """Test that empty dict is returned for non-existent file."""
        yaml_path = tmp_path / "nonexistent.yml"
        loaded = rs._load_yaml(yaml_path)
        assert loaded == {}

    def test_handles_empty_yaml_file(self, tmp_path):
        """Test handling of empty YAML file."""
        yaml_path = tmp_path / "empty.yml"
        yaml_path.write_text("", encoding="utf-8")

        loaded = rs._load_yaml(yaml_path)
        assert loaded == {}

    def test_handles_yaml_with_unicode(self, tmp_path):
        """Test loading YAML with Unicode characters."""
        yaml_path = tmp_path / "unicode.yml"
        data = {"spanish": "Niño", "emoji": "🎉"}
        yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

        loaded = rs._load_yaml(yaml_path)
        assert loaded["spanish"] == "Niño"
        assert loaded["emoji"] == "🎉"


class TestWriteYamlAtomic:
    """Test _write_yaml_atomic helper function."""

    def test_writes_valid_yaml(self, tmp_path):
        """Test writing valid YAML atomically."""
        yaml_path = tmp_path / "write.yml"
        data = {"test": "value", "list": [1, 2, 3]}

        rs._write_yaml_atomic(yaml_path, data)

        assert yaml_path.exists()
        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert loaded == data

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        yaml_path = tmp_path / "nested" / "dir" / "file.yml"
        data = {"nested": "test"}

        rs._write_yaml_atomic(yaml_path, data)

        assert yaml_path.exists()
        assert yaml_path.parent.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Test that existing file is overwritten."""
        yaml_path = tmp_path / "overwrite.yml"
        yaml_path.write_text(yaml.safe_dump({"old": "data"}), encoding="utf-8")

        rs._write_yaml_atomic(yaml_path, {"new": "data"})

        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert loaded == {"new": "data"}
        assert "old" not in loaded

    def test_preserves_unicode_characters(self, tmp_path):
        """Test that Unicode characters are preserved."""
        yaml_path = tmp_path / "unicode.yml"
        data = {"spanish": "Niño", "japanese": "日本語"}

        rs._write_yaml_atomic(yaml_path, data)

        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert loaded["spanish"] == "Niño"
        assert loaded["japanese"] == "日本語"

    def test_does_not_leave_temp_file(self, tmp_path):
        """Test that temporary file is cleaned up."""
        yaml_path = tmp_path / "cleanup.yml"
        rs._write_yaml_atomic(yaml_path, {"test": "data"})

        # Check temp file doesn't exist
        temp_path = yaml_path.with_suffix(yaml_path.suffix + ".tmp")
        assert not temp_path.exists()


class TestBuildRule:
    """Test build_rule function."""

    def test_builds_rule_with_correct_structure(self):
        """Test that rule is built with correct structure."""
        rule = rs.build_rule("amazon", "amazon.*", "Expenses:Shopping", "online")

        assert rule["name"] == "UserCorrection:amazon"
        assert rule["any_regex"] == ["amazon.*"]
        assert rule["set"]["expense"] == "Expenses:Shopping"
        assert rule["set"]["tags"] == ["bucket:online"]

    def test_formats_merchant_name_in_rule_name(self):
        """Test that merchant name is properly formatted in rule name."""
        rule = rs.build_rule("test_merchant", "pattern", "Expenses:Test", "test")
        assert rule["name"] == "UserCorrection:test_merchant"

    def test_handles_special_characters(self):
        """Test handling of special characters in inputs."""
        rule = rs.build_rule("store.com", "store\\.com", "Expenses:Other", "misc")

        assert "store.com" in rule["name"]
        assert "store\\.com" in rule["any_regex"]


class TestRuleRegexes:
    """Test _rule_regexes helper function."""

    def test_extracts_regexes_from_rule(self):
        """Test extraction of regex list from rule."""
        rule = {"any_regex": ["pattern1", "pattern2", "pattern3"]}
        regexes = rs._rule_regexes(rule)

        assert len(regexes) == 3
        assert "pattern1" in regexes
        assert "pattern2" in regexes
        assert "pattern3" in regexes

    def test_handles_missing_any_regex_key(self):
        """Test handling when any_regex key is missing."""
        rule = {"name": "Test"}
        regexes = rs._rule_regexes(rule)
        assert regexes == []

    def test_handles_none_any_regex(self):
        """Test handling when any_regex is None."""
        rule = {"any_regex": None}
        regexes = rs._rule_regexes(rule)
        assert regexes == []

    def test_strips_whitespace_from_regexes(self):
        """Test that whitespace is stripped from regex patterns."""
        rule = {"any_regex": ["  pattern1  ", " pattern2 "]}
        regexes = rs._rule_regexes(rule)

        assert "pattern1" in regexes
        assert "pattern2" in regexes

    def test_filters_empty_strings(self):
        """Test that empty strings are filtered out."""
        rule = {"any_regex": ["pattern1", "", "   ", "pattern2"]}
        regexes = rs._rule_regexes(rule)

        assert len(regexes) == 2
        assert "pattern1" in regexes
        assert "pattern2" in regexes


class TestDetectConflicts:
    """Test detect_conflicts function."""

    def test_detects_name_conflict(self):
        """Test detection of conflicting rule names."""
        existing = [{"name": "TestRule", "any_regex": ["pattern1"]}]
        candidate = {"name": "TestRule", "any_regex": ["pattern2"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        assert "name:TestRule" in conflicts

    def test_detects_regex_conflict(self):
        """Test detection of conflicting regex patterns."""
        existing = [{"name": "Rule1", "any_regex": ["amazon", "walmart"]}]
        candidate = {"name": "Rule2", "any_regex": ["target", "amazon"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        assert "regex:amazon" in conflicts

    def test_detects_multiple_conflicts(self):
        """Test detection of multiple conflicts."""
        existing = [
            {"name": "Rule1", "any_regex": ["pattern1", "pattern2"]},
            {"name": "Rule2", "any_regex": ["pattern3"]}
        ]
        candidate = {"name": "Rule1", "any_regex": ["pattern2", "pattern3"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        assert "name:Rule1" in conflicts
        assert "regex:pattern2" in conflicts
        assert "regex:pattern3" in conflicts

    def test_returns_empty_list_when_no_conflicts(self):
        """Test that empty list is returned when no conflicts exist."""
        existing = [{"name": "Rule1", "any_regex": ["pattern1"]}]
        candidate = {"name": "Rule2", "any_regex": ["pattern2"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        assert conflicts == []

    def test_handles_empty_existing_rules(self):
        """Test handling of empty existing rules list."""
        existing = []
        candidate = {"name": "Rule1", "any_regex": ["pattern1"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        assert conflicts == []

    def test_conflicts_are_deduplicated(self):
        """Test that duplicate conflicts are removed."""
        existing = [
            {"name": "Rule1", "any_regex": ["pattern1"]},
            {"name": "Rule2", "any_regex": ["pattern1"]}
        ]
        candidate = {"name": "Rule3", "any_regex": ["pattern1"]}

        conflicts = rs.detect_conflicts(existing, candidate)

        # Should only have one regex conflict despite multiple matches
        regex_conflicts = [c for c in conflicts if c.startswith("regex:")]
        assert len(regex_conflicts) == 1


class TestGetPendingCount:
    """Test get_pending_count function."""

    def test_returns_count_of_pending_rules(self, tmp_path):
        """Test that correct count is returned for pending rules."""
        pending_path = tmp_path / "pending.yml"
        data = {
            "pending_rules": [
                {"name": "Rule1", "any_regex": ["p1"]},
                {"name": "Rule2", "any_regex": ["p2"]},
                {"name": "Rule3", "any_regex": ["p3"]}
            ]
        }
        pending_path.write_text(yaml.safe_dump(data), encoding="utf-8")

        count = rs.get_pending_count(pending_path)
        assert count == 3

    def test_returns_zero_when_file_not_exists(self, tmp_path):
        """Test that 0 is returned when file doesn't exist."""
        pending_path = tmp_path / "nonexistent.yml"
        count = rs.get_pending_count(pending_path)
        assert count == 0

    def test_returns_zero_when_no_pending_rules(self, tmp_path):
        """Test that 0 is returned when pending_rules list is empty."""
        pending_path = tmp_path / "empty.yml"
        data = {"pending_rules": []}
        pending_path.write_text(yaml.safe_dump(data), encoding="utf-8")

        count = rs.get_pending_count(pending_path)
        assert count == 0

    def test_handles_missing_pending_rules_key(self, tmp_path):
        """Test handling when pending_rules key is missing."""
        pending_path = tmp_path / "no_key.yml"
        data = {"other_key": "value"}
        pending_path.write_text(yaml.safe_dump(data), encoding="utf-8")

        count = rs.get_pending_count(pending_path)
        assert count == 0


class TestMergePendingRulesEdgeCases:
    """Test edge cases for merge_pending_rules function."""

    def test_returns_no_pending_when_file_missing(self, tmp_path):
        """Test handling when pending file doesn't exist."""
        rules_path = tmp_path / "rules.yml"
        pending_path = tmp_path / "pending.yml"
        backup_dir = tmp_path / "backups"

        _seed_rules(rules_path)

        ok, result = rs.merge_pending_rules(rules_path, pending_path, backup_dir)

        assert ok is False
        assert result["status"] == "no_pending"

    def test_detects_conflicts_during_merge(self, tmp_path):
        """Test conflict detection during merge operation."""
        rules_path = tmp_path / "rules.yml"
        pending_path = tmp_path / "pending.yml"
        backup_dir = tmp_path / "backups"

        # Seed with existing rule
        _seed_rules(rules_path)

        # Create pending with conflicting rule
        pending_data = {
            "pending_rules": [
                {
                    "name": "Groceries",  # Name conflict
                    "any_regex": ["target"],
                    "set": {"expense": "Expenses:Food", "tags": ["bucket:food"]}
                }
            ]
        }
        pending_path.write_text(yaml.safe_dump(pending_data), encoding="utf-8")

        ok, result = rs.merge_pending_rules(rules_path, pending_path, backup_dir)

        assert ok is False
        assert result["status"] == "conflict"
        assert len(result["conflicts"]) > 0
