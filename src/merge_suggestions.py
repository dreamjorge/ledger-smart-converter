#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Merge + clean Firefly rules:
- Input: rules.yml (base) + rules_suggestions.yml (output from assisted learning)
- Fixes:
  - tags that accidentally become dicts like {"merchant": "amazon"} -> "merchant:amazon"
  - regex normalization: converts escaped spaces "\ " to "\s+"
  - de-duplicates suggested rules
  - consolidates families (oxxo, cinepolis, walmart, gas, etc.) into fewer rules + aliases
- Output: rules_merged.yml

Usage:
  python3 merge_suggestions.py --base rules.yml --suggestions rules_suggestions.yml --out rules_merged.yml
"""

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

import yaml


# ----------------------------
# Helpers
# ----------------------------

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def ensure_str_tag(tag: Any) -> Optional[str]:
    """
    Fix tags like:
      - "merchant:amazon" -> same
      - {"merchant":"amazon"} -> "merchant:amazon"
      - {"bucket":"groceries"} -> "bucket:groceries"
    """
    if tag is None:
        return None
    if isinstance(tag, str):
        t = tag.strip()
        return t if t else None
    if isinstance(tag, dict) and len(tag) == 1:
        k, v = next(iter(tag.items()))
        k = str(k).strip()
        v = str(v).strip()
        if k and v:
            return f"{k}:{v}"
    # fallback
    t = str(tag).strip()
    return t if t else None


def normalize_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        tags = [tags]
    out = []
    for t in tags:
        s = ensure_str_tag(t)
        if s:
            out.append(s)
    # dedup preserve order
    seen = set()
    res = []
    for t in out:
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res


def normalize_regex(rx: str) -> str:
    """
    Makes regex more robust:
    - Turns escaped spaces '\\ ' or '\ ' into '\\s+'
    - Collapses multiple space tokens into '\\s+'
    - Keeps user intent (we don't over-aggressively rewrite)
    """
    if not rx:
        return rx
    r = rx.strip()

    # remove surrounding parentheses if it's exactly "(...)" (optional but helpful)
    # Only if it is a single outer pair
    if r.startswith("(") and r.endswith(")"):
        inner = r[1:-1].strip()
        # avoid breaking groups like (a|b)
        r = inner

    # Replace escaped space patterns with \s+
    r = r.replace(r"\ ", r"\s+")
    # Replace literal multiple spaces with \s+
    r = re.sub(r"\s{2,}", r"\\s+", r)

    return r


def rule_key(rule: Dict[str, Any]) -> Tuple:
    """
    Stable key for de-dup.
    """
    name = str(rule.get("name", "")).strip().lower()
    any_rx = tuple(sorted((rule.get("any_regex") or [])))
    expense = (rule.get("set") or {}).get("expense", "")
    tags = tuple(sorted(normalize_tags((rule.get("set") or {}).get("tags"))))
    return (name, any_rx, expense, tags)


# ----------------------------
# Family consolidation heuristics
# ----------------------------

FAMILY_PATTERNS = {
    "oxxo": re.compile(r"\boxxo\b", re.IGNORECASE),
    "cinepolis": re.compile(r"cinepolis|ppcinepolis", re.IGNORECASE),
    "walmart": re.compile(r"wal\s*mart|wm\s*express|\bwalmart\b", re.IGNORECASE),
    "gas_station": re.compile(r"gasol|gaso|carburantes|novogas", re.IGNORECASE),
    "mercadopago": re.compile(r"merpago|mercado\s*pago", re.IGNORECASE),
    "paypal": re.compile(r"\bpaypal\b", re.IGNORECASE),
    "conekta": re.compile(r"\bconekta\b", re.IGNORECASE),
    "miniso": re.compile(r"\bminiso\b", re.IGNORECASE),
    "televia": re.compile(r"\btelevia\b", re.IGNORECASE),
}


def pick_family(merchant: str, rx_list: List[str]) -> str:
    s = merchant.replace("_", " ")
    joined = " ".join(rx_list + [s])
    for fam, pat in FAMILY_PATTERNS.items():
        if pat.search(joined):
            return fam
    return "other"


def family_defaults() -> Dict[str, Dict[str, Any]]:
    """
    Proposed default mapping.
    You can edit these later.
    """
    return {
        "oxxo":        {"expense": "Expenses:Food:Convenience",      "tags": ["bucket:convenience"]},
        "cinepolis":   {"expense": "Expenses:Entertainment:Cinema",  "tags": ["bucket:entertainment"]},
        "walmart":     {"expense": "Expenses:Food:Groceries",        "tags": ["bucket:groceries"]},
        "gas_station": {"expense": "Expenses:Transport:Fuel",        "tags": ["bucket:fuel"]},
        "mercadopago": {"expense": "Expenses:Shopping:Online",       "tags": ["bucket:online"]},
        "paypal":      {"expense": "Expenses:Shopping:Online",       "tags": ["bucket:online"]},
        "conekta":     {"expense": "Expenses:Shopping:Online",       "tags": ["bucket:online"]},
        "miniso":      {"expense": "Expenses:Shopping:Retail",       "tags": ["bucket:retail"]},
        "televia":     {"expense": "Expenses:Transport:Tolls",       "tags": ["bucket:tolls"]},
        "other":       {"expense": "Expenses:Other:Uncategorized",   "tags": []},
    }


def build_merchant_alias_entry(canon: str, rx_list: List[str]) -> Dict[str, Any]:
    # ensure regexes are compact and dedup
    cleaned = []
    seen = set()
    for r in rx_list:
        r2 = normalize_regex(r)
        if not r2:
            continue
        if r2 not in seen:
            seen.add(r2)
            cleaned.append(r2)
    return {"canon": canon, "any_regex": cleaned}


def build_family_rule(family: str, rx_list: List[str], fam_cfg: Dict[str, Any]) -> Dict[str, Any]:
    # Make a single rule for a family using the aggregated regexes
    cleaned = []
    seen = set()
    for r in rx_list:
        r2 = normalize_regex(r)
        if not r2:
            continue
        if r2 not in seen:
            seen.add(r2)
            cleaned.append(r2)

    return {
        "name": f"Auto:{family}",
        "any_regex": cleaned if cleaned else [family],
        "set": {
            "expense": fam_cfg["expense"],
            "tags": fam_cfg["tags"],
        },
    }


# ----------------------------
# Merge logic
# ----------------------------

def merge_rules(base: Dict[str, Any], suggestions: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)  # shallow copy

    # Ensure basic keys
    out.setdefault("version", 1)
    out.setdefault("defaults", {})
    out.setdefault("merchant_aliases", [])
    out.setdefault("rules", [])

    base_aliases: List[Dict[str, Any]] = out.get("merchant_aliases") or []
    base_rules: List[Dict[str, Any]] = out.get("rules") or []

    # Index existing aliases by canon
    alias_by_canon: Dict[str, Dict[str, Any]] = {}
    for a in base_aliases:
        canon = str(a.get("canon", "")).strip()
        if not canon:
            continue
        alias_by_canon[canon] = a

    # Normalize base rules tags
    for r in base_rules:
        s = r.get("set") or {}
        s["tags"] = normalize_tags(s.get("tags"))
        r["set"] = s

    # --- Read suggestions list ---
    suggested_rules = suggestions.get("suggested_rules") or suggestions.get("rules") or []
    # Normalize suggested rules
    normalized_suggestions = []
    for r in suggested_rules:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name", "")).strip() or "TODO"
        any_rx = r.get("any_regex") or []
        if not isinstance(any_rx, list):
            any_rx = [any_rx]
        any_rx = [normalize_regex(str(x)) for x in any_rx if str(x).strip()]
        s = r.get("set") or {}
        s_tags = normalize_tags(s.get("tags"))
        s_exp = str(s.get("expense", "")).strip() or "Expenses:Other:Uncategorized"
        normalized_suggestions.append({
            "name": name,
            "any_regex": any_rx,
            "set": {"expense": s_exp, "tags": s_tags},
        })

    # --- Consolidate by merchant:<canon> tag if present ---
    # We use merchant tag to find canon if exists, otherwise infer from rule name "TODO_xxx"
    merchant_to_regexes: Dict[str, List[str]] = defaultdict(list)

    for r in normalized_suggestions:
        tags = r["set"]["tags"]
        canon = None
        for t in tags:
            if t.startswith("merchant:"):
                canon = t.split("merchant:", 1)[1].strip()
                break
        if not canon:
            # fallback from name: TODO_xxx
            m = re.match(r"todo_(.+)", r["name"], flags=re.IGNORECASE)
            canon = m.group(1).strip() if m else r["name"].strip().lower()

        canon = canon.replace(" ", "_")
        for rx in r["any_regex"]:
            if rx:
                merchant_to_regexes[canon].append(rx)

    # --- Build consolidated aliases + family rules ---
    fam_cfgs = family_defaults()

    # Group merchants into families
    family_to_rx: Dict[str, List[str]] = defaultdict(list)
    family_to_merchants: Dict[str, List[str]] = defaultdict(list)

    for canon, rx_list in merchant_to_regexes.items():
        fam = pick_family(canon, rx_list)
        family_to_merchants[fam].append(canon)
        # for family-level rule: include canonical tokens + individual regexes
        family_to_rx[fam].extend(rx_list + [canon.replace("_", r"\s+")])

        # Add/merge merchant alias entry
        if canon in alias_by_canon:
            existing = alias_by_canon[canon]
            existing_list = existing.get("any_regex") or []
            if not isinstance(existing_list, list):
                existing_list = [existing_list]
            merged = list(existing_list) + rx_list
            existing["any_regex"] = list(dict.fromkeys([normalize_regex(str(x)) for x in merged if str(x).strip()]))
        else:
            alias_by_canon[canon] = build_merchant_alias_entry(canon, rx_list)

    # Build new alias list (sorted by canon)
    out["merchant_aliases"] = [alias_by_canon[k] for k in sorted(alias_by_canon.keys())]

    # Build consolidated rules for families (but don't duplicate if base already has similar)
    existing_rule_names = {str(r.get("name", "")).strip().lower() for r in base_rules}

    consolidated_family_rules = []
    for fam, rx_list in family_to_rx.items():
        fam_rule_name = f"Auto:{fam}".lower()
        if fam_rule_name in existing_rule_names:
            continue
        cfg = fam_cfgs.get(fam, fam_cfgs["other"])
        consolidated_family_rules.append(build_family_rule(fam, rx_list, cfg))

    # Place consolidated rules near the top, before the base rules (so they match early)
    out["rules"] = consolidated_family_rules + base_rules

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Base rules.yml")
    ap.add_argument("--suggestions", required=True, help="rules_suggestions.yml")
    ap.add_argument("--out", required=True, help="Output merged yaml")
    args = ap.parse_args()

    base_path = Path(args.base)
    sugg_path = Path(args.suggestions)
    out_path = Path(args.out)

    if not base_path.exists():
        print(f"ERROR: base file not found: {base_path}")
        return 2
    if not sugg_path.exists():
        print(f"ERROR: suggestions file not found: {sugg_path}")
        return 2

    base = load_yaml(base_path)
    sugg = load_yaml(sugg_path)

    merged = merge_rules(base, sugg)
    dump_yaml(out_path, merged)

    print("OK")
    print(f"Merged rules written to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
