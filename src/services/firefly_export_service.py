from pathlib import Path
from typing import Optional

import pandas as pd

from services.db_service import DatabaseService


def export_firefly_csv_from_db(
    db_path: Path,
    out_csv: Path,
    bank_id: Optional[str] = None,
) -> int:
    db = DatabaseService(db_path=db_path)
    query = (
        "SELECT type, date, amount, currency_code, description, source_name, "
        "destination_name, category_name, tags "
        "FROM firefly_export"
    )
    params = []
    if bank_id:
        query += " WHERE bank_id = ?"
        params.append(bank_id)
    query += " ORDER BY date, description"

    rows = db.fetch_all(query, tuple(params))
    df = pd.DataFrame(rows)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return len(df)
