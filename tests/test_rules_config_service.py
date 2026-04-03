from services.rules_config_service import (
    load_bank_display_names,
    load_expense_categories,
    load_rules_config,
)


def test_load_rules_config_returns_empty_dict_for_missing_file(tmp_path):
    rules_path = tmp_path / "missing.yml"

    assert load_rules_config(rules_path) == {}


def test_load_expense_categories_returns_sorted_unique_canonical_values(tmp_path):
    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        """
defaults:
  fallback_expense: Expenses:Other:Uncategorized
rules:
  - set:
      expense: Expenses:Food:Groceries
  - set:
      expense: Expenses:Food:Restaurants
  - set:
      expense: Expenses:Food:Groceries
  - set: {}
""".strip(),
        encoding="utf-8",
    )

    assert load_expense_categories(rules_path) == [
        "Expenses:Food:Groceries",
        "Expenses:Food:Restaurants",
        "Expenses:Other:Uncategorized",
    ]


def test_load_bank_display_names_prefers_display_name_and_falls_back_to_bank_id(
    tmp_path,
):
    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        """
banks:
  santander_likeu:
    display_name: Santander LikeU
  hsbc:
    name: HSBC Mexico
""".strip(),
        encoding="utf-8",
    )

    assert load_bank_display_names(rules_path) == {
        "santander_likeu": "Santander LikeU",
        "hsbc": "hsbc",
    }
