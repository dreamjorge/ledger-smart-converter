from typing import Any, Dict, Optional

import pandas as pd


def calculate_categorization_stats(df: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    if df is None:
        return None
    if df.empty:
        return {
            "total": 0,
            "categorized": 0,
            "uncategorized": 0,
            "coverage_pct": 0,
            "category_populated": 0,
            "category_pct": 0,
            "total_spent": 0.0,
            "type_counts": {},
            "categories": {},
            "category_spending": {},
        }

    total = len(df)
    if "destination_name" in df.columns:
        uncategorized = df["destination_name"].str.contains("Uncategorized", case=False, na=False).sum()
        categorized = total - uncategorized
    else:
        categorized = 0
        uncategorized = total

    if "category_name" in df.columns:
        has_category = df["category_name"].notna() & (df["category_name"] != "")
        category_populated = has_category.sum()
    else:
        category_populated = 0

    total_spent = 0.0
    if "amount" in df.columns and "type" in df.columns:
        total_spent = df[df["type"] == "withdrawal"]["amount"].astype(float).sum()

    type_counts = df["type"].value_counts().to_dict() if "type" in df.columns else {}
    categories = {}
    category_spending = {}
    if "destination_name" in df.columns and "amount" in df.columns:
        for _, row in df.iterrows():
            dest = row["destination_name"]
            amt = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
            if pd.notna(dest) and ":" in str(dest):
                parts = str(dest).split(":")
                if len(parts) > 1 and parts[0] == "Expenses":
                    cat = parts[1]
                    categories[cat] = categories.get(cat, 0) + 1
                    if row.get("type") == "withdrawal":
                        category_spending[cat] = category_spending.get(cat, 0.0) + amt

    return {
        "total": total,
        "categorized": categorized,
        "uncategorized": uncategorized,
        "coverage_pct": (categorized / total * 100) if total > 0 else 0,
        "category_populated": category_populated,
        "category_pct": (category_populated / total * 100) if total > 0 else 0,
        "total_spent": total_spent,
        "type_counts": type_counts,
        "categories": categories,
        "category_spending": category_spending,
    }
