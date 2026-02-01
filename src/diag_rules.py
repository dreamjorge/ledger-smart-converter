import yaml
import re
from pathlib import Path
import common_utils as cu

rules_path = Path("config/rules.yml")
rules_yml = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
compiled = cu.compile_rules(rules_yml)
merchant_aliases = rules_yml.get("merchant_aliases", []) or []
fallback_expense = rules_yml.get("defaults", {}).get("fallback_expense", "Expenses:Other:Uncategorized")

test_cases = [
    "STR AMAZON CIU",
    "VENTUS SPORT MATRIZ SAN",
    "MPIO EL MARQUES APP 2 SAN",
    "G GASO SIETE MADERO SAN",
    "CINEPOLIS DULCERIA MOR"
]

for desc in test_cases:
    expense, tags, merchant = cu.classify(desc, compiled, merchant_aliases, fallback_expense)
    print(f"Desc: {desc}")
    print(f"  Merchant: {merchant}")
    print(f"  Expense: {expense}")
    print(f"  Tags: {tags}")
    print("-" * 20)
