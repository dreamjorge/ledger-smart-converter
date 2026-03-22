from pathlib import Path
from typing import Optional

import pandas as pd

from services.db_service import DatabaseService

FIREFLY_COLUMNS = [
    "type", "date", "amount", "currency_code",
    "description", "source_name", "destination_name",
    "category_name", "tags",
]


def export_firefly_csv_from_db(
    db_path: Path,
    out_csv: Path,
    bank_id: Optional[str] = None,
    use_normalized_description: bool = False,
) -> int:
    """Export transactions from DB to Firefly III-compatible CSV.

    Returns number of rows exported.
    """
    db = DatabaseService(db_path=db_path)
    desc_col = (
        "COALESCE(normalized_description, description)"
        if use_normalized_description
        else "description"
    )
    query = (
        f"SELECT type, date, amount, currency_code, {desc_col} AS description, "
        "source_name, destination_name, category_name, tags, bank_id "
        "FROM firefly_export"
    )
    params: list = []
    if bank_id:
        query += " WHERE bank_id = ?"
        params.append(bank_id)
    query += " ORDER BY date, description"

    rows = db.fetch_all(query, tuple(params))

    if rows:
        df = pd.DataFrame(rows)
        export_df = df[FIREFLY_COLUMNS]
    else:
        export_df = pd.DataFrame(columns=FIREFLY_COLUMNS)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(out_csv, index=False)
    return len(export_df)
