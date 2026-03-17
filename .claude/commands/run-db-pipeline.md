Run the full DB pipeline: discover firefly CSVs, migrate to SQLite, backfill normalized descriptions, and export Firefly CSVs.

```bash
python scripts/run_db_pipeline.py \
  --db data/ledger.db \
  --data-dir data \
  --accounts config/accounts.yml
```

To verify after running:
```bash
sqlite3 data/ledger.db "SELECT bank_id, count(*) FROM transactions GROUP BY bank_id"
sqlite3 data/ledger.db "SELECT bank_id, status, row_count FROM imports ORDER BY processed_at DESC LIMIT 5"
```
