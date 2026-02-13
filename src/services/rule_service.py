from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from services.db_service import DatabaseService


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _write_yaml_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    tmp.replace(path)


def build_rule(merchant_name: str, regex_pattern: str, expense_account: str, bucket_tag: str) -> Dict[str, Any]:
    return {
        "name": f"UserCorrection:{merchant_name}",
        "any_regex": [regex_pattern],
        "set": {
            "expense": expense_account,
            "tags": [f"bucket:{bucket_tag}"],
        },
    }


def _rule_regexes(rule: Dict[str, Any]) -> List[str]:
    return [str(rx).strip() for rx in (rule.get("any_regex", []) or []) if str(rx).strip()]


def detect_conflicts(existing_rules: List[Dict[str, Any]], candidate_rule: Dict[str, Any]) -> List[str]:
    conflicts: List[str] = []
    candidate_name = str(candidate_rule.get("name", "")).strip()
    candidate_rx = set(_rule_regexes(candidate_rule))
    for rule in existing_rules:
        name = str(rule.get("name", "")).strip()
        if candidate_name and candidate_name == name:
            conflicts.append(f"name:{candidate_name}")
        overlap = candidate_rx.intersection(set(_rule_regexes(rule)))
        for rx in sorted(overlap):
            conflicts.append(f"regex:{rx}")
    return sorted(set(conflicts))


def stage_rule_change(
    rules_path: Path,
    pending_path: Path,
    merchant_name: str,
    regex_pattern: str,
    expense_account: str,
    bucket_tag: str,
    db_path: Path = None,
) -> Tuple[bool, Dict[str, Any]]:
    config = _load_yaml(rules_path)
    existing = config.get("rules", [])
    candidate = build_rule(merchant_name, regex_pattern, expense_account, bucket_tag)
    conflicts = detect_conflicts(existing, candidate)
    if conflicts:
        return False, {"status": "conflict", "conflicts": conflicts}

    pending = _load_yaml(pending_path)
    pending_rules = pending.get("pending_rules", [])
    pending_conflicts = detect_conflicts(pending_rules, candidate)
    if pending_conflicts:
        return False, {"status": "conflict_pending", "conflicts": pending_conflicts}

    pending_rules.append(candidate)
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pending_rules": pending_rules,
    }
    _write_yaml_atomic(pending_path, payload)
    if db_path:
        db = DatabaseService(db_path=Path(db_path))
        db.initialize()
        db.record_audit_event(
            event_type="rule_staged",
            entity_type="rule",
            entity_id=candidate.get("name", ""),
            payload={
                "merchant_name": merchant_name,
                "regex_pattern": regex_pattern,
                "expense_account": expense_account,
                "bucket_tag": bucket_tag,
            },
        )
    return True, {"status": "staged", "pending_count": len(pending_rules)}


def merge_pending_rules(
    rules_path: Path,
    pending_path: Path,
    backup_dir: Path,
    db_path: Path = None,
) -> Tuple[bool, Dict[str, Any]]:
    if not pending_path.exists():
        return False, {"status": "no_pending"}

    config = _load_yaml(rules_path)
    rules = list(config.get("rules", []))
    pending = _load_yaml(pending_path)
    pending_rules = pending.get("pending_rules", [])
    if not pending_rules:
        return False, {"status": "no_pending"}

    conflicts: List[Dict[str, Any]] = []
    merged: List[Dict[str, Any]] = []
    working = list(rules)
    for candidate in pending_rules:
        found = detect_conflicts(working, candidate)
        if found:
            conflicts.append({"rule": candidate.get("name", "unknown"), "conflicts": found})
            continue
        merged.append(candidate)
        working.insert(0, candidate)

    if conflicts:
        return False, {"status": "conflict", "conflicts": conflicts, "mergeable_count": len(merged)}

    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_path = backup_dir / f"rules.{ts}.yml"
    backup_path.write_text(rules_path.read_text(encoding="utf-8"), encoding="utf-8")

    config["rules"] = working
    _write_yaml_atomic(rules_path, config)
    pending_path.unlink(missing_ok=True)
    if db_path:
        db = DatabaseService(db_path=Path(db_path))
        db.initialize()
        db.record_audit_event(
            event_type="rules_merged",
            entity_type="ruleset",
            entity_id=str(rules_path),
            payload={
                "merged_count": len(merged),
                "backup_path": str(backup_path),
            },
        )
    return True, {
        "status": "merged",
        "merged_count": len(merged),
        "backup_path": str(backup_path),
    }


def get_pending_count(pending_path: Path) -> int:
    if not pending_path.exists():
        return 0
    pending = _load_yaml(pending_path)
    return len(pending.get("pending_rules", []))


def record_recategorization_event(
    db_path: Path,
    transaction_source_hash: str,
    old_category: str,
    new_category: str,
    reason: str = "",
) -> int:
    db = DatabaseService(db_path=Path(db_path))
    db.initialize()
    return db.record_audit_event(
        event_type="recategorization",
        entity_type="transaction",
        entity_id=transaction_source_hash,
        payload={
            "old_category": old_category,
            "new_category": new_category,
            "reason": reason,
        },
    )
