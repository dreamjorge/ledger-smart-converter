from pathlib import Path

import merge_suggestions as ms


def test_ensure_str_tag_handles_string_and_empty():
    assert ms.ensure_str_tag(" merchant:amazon ") == "merchant:amazon"
    assert ms.ensure_str_tag("   ") is None


def test_ensure_str_tag_handles_dict_and_none():
    assert ms.ensure_str_tag({"merchant": "amazon"}) == "merchant:amazon"
    assert ms.ensure_str_tag(None) is None


def test_normalize_tags_handles_single_value_and_dedup():
    result = ms.normalize_tags(["merchant:amazon", {"bucket": "online"}, "merchant:amazon"])
    assert result == ["merchant:amazon", "bucket:online"]


def test_normalize_regex_rewrites_spaces_and_trims_parentheses():
    assert ms.normalize_regex(r"(amazon\ market)") == r"amazon\s+market"
    assert ms.normalize_regex("foo    bar") == r"foo\s+bar"


def test_rule_key_normalizes_name_and_tags():
    rule = {
        "name": "  TEST RULE ",
        "any_regex": ["b", "a"],
        "set": {"expense": "Expenses:Test", "tags": [{"merchant": "a"}, "bucket:x"]},
    }
    key = ms.rule_key(rule)
    assert key[0] == "test rule"
    assert key[1] == ("a", "b")
    assert key[2] == "Expenses:Test"
    assert key[3] == ("bucket:x", "merchant:a")


def test_pick_family_matches_known_patterns_and_fallback():
    assert ms.pick_family("amazon", [r"cinepolis\s+ticket"]) == "cinepolis"
    assert ms.pick_family("unknown_merchant", []) == "other"


def test_family_defaults_contains_expected_keys():
    defaults = ms.family_defaults()
    assert "oxxo" in defaults
    assert "other" in defaults
    assert defaults["other"]["expense"] == "Expenses:Other:Uncategorized"


def test_build_merchant_alias_entry_dedups_and_normalizes_regex():
    entry = ms.build_merchant_alias_entry("amazon", [r"amazon\ market", r"amazon\ market", ""])
    assert entry["canon"] == "amazon"
    assert entry["any_regex"] == [r"amazon\s+market"]


def test_build_family_rule_uses_family_config():
    cfg = {"expense": "Expenses:Food:Groceries", "tags": ["bucket:groceries"]}
    rule = ms.build_family_rule("walmart", [r"wal\ mart"], cfg)
    assert rule["name"] == "Auto:walmart"
    assert rule["any_regex"] == [r"wal\s+mart"]
    assert rule["set"]["expense"] == "Expenses:Food:Groceries"
    assert rule["set"]["tags"] == ["bucket:groceries"]


def test_load_and_dump_yaml_roundtrip(tmp_path):
    out = tmp_path / "nested" / "rules.yml"
    data = {"version": 1, "rules": [{"name": "A"}]}
    ms.dump_yaml(out, data)
    loaded = ms.load_yaml(out)
    assert loaded == data


def test_merge_rules_adds_consolidated_aliases_and_family_rules():
    base = {
        "version": 1,
        "merchant_aliases": [{"canon": "amazon", "any_regex": ["amazon"]}],
        "rules": [{"name": "Existing", "any_regex": ["foo"], "set": {"expense": "Expenses:X", "tags": None}}],
    }
    suggestions = {
        "suggested_rules": [
            {
                "name": "TODO_amazon",
                "any_regex": [r"amzn\ mx"],
                "set": {"expense": "Expenses:Shopping:Online", "tags": [{"merchant": "amazon"}]},
            },
            {
                "name": "TODO_cinepolis",
                "any_regex": [r"cinepolis\ qro"],
                "set": {"tags": ["merchant:cinepolis"]},
            },
        ]
    }

    merged = ms.merge_rules(base, suggestions)

    aliases_by_canon = {a["canon"]: a["any_regex"] for a in merged["merchant_aliases"]}
    assert "amazon" in aliases_by_canon
    assert r"amzn\s+mx" in aliases_by_canon["amazon"]
    assert "cinepolis" in aliases_by_canon

    rule_names = [r["name"] for r in merged["rules"]]
    assert "Auto:mercadopago" not in rule_names
    assert "Auto:cinepolis" in rule_names
    assert "Existing" in rule_names
    existing_rule = next(r for r in merged["rules"] if r["name"] == "Existing")
    assert existing_rule["set"]["tags"] == []


def test_merge_rules_avoids_duplicate_auto_rule_name():
    base = {
        "merchant_aliases": [],
        "rules": [{"name": "Auto:oxxo", "any_regex": ["oxxo"], "set": {"expense": "Expenses:Food", "tags": []}}],
    }
    suggestions = {
        "rules": [
            {
                "name": "TODO_oxxo",
                "any_regex": ["oxxo qro"],
                "set": {"tags": ["merchant:oxxo"]},
            }
        ]
    }
    merged = ms.merge_rules(base, suggestions)
    names = [r["name"].lower() for r in merged["rules"]]
    assert names.count("auto:oxxo") == 1


def test_main_returns_2_when_input_files_missing(monkeypatch):
    monkeypatch.setattr(ms, "Path", Path)
    args = ["prog", "--base", "missing_base.yml", "--suggestions", "missing_sugg.yml", "--out", "out.yml"]
    monkeypatch.setattr("sys.argv", args)
    assert ms.main() == 2


def test_main_writes_merged_file_and_returns_0(tmp_path, monkeypatch):
    base_path = tmp_path / "base.yml"
    sugg_path = tmp_path / "sugg.yml"
    out_path = tmp_path / "out.yml"

    ms.dump_yaml(base_path, {"version": 1, "merchant_aliases": [], "rules": []})
    ms.dump_yaml(
        sugg_path,
        {
            "suggested_rules": [
                {"name": "TODO_walmart", "any_regex": ["wal mart"], "set": {"tags": ["merchant:walmart"]}}
            ]
        },
    )

    args = ["prog", "--base", str(base_path), "--suggestions", str(sugg_path), "--out", str(out_path)]
    monkeypatch.setattr("sys.argv", args)

    assert ms.main() == 0
    assert out_path.exists()
    merged = ms.load_yaml(out_path)
    assert isinstance(merged.get("rules"), list)
