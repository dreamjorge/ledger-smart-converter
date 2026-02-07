import pandas as pd

from services.analytics_service import calculate_categorization_stats


def test_calculate_categorization_stats_basic():
    df = pd.DataFrame(
        [
            {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food:Groceries", "category_name": "Food"},
            {"type": "transfer", "amount": 200.0, "destination_name": "Assets:Cash", "category_name": ""},
            {"type": "withdrawal", "amount": 50.0, "destination_name": "Expenses:Other:Uncategorized", "category_name": "Other"},
        ]
    )
    stats = calculate_categorization_stats(df)
    assert stats["total"] == 3
    assert stats["uncategorized"] == 1
    assert stats["categorized"] == 2
    assert stats["total_spent"] == 150.0
    assert stats["categories"]["Food"] == 1
