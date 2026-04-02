## Exploration: SQLite Persistence

### Current State
The project already has a semi-implemented SQLite infrastructure. 
- `src/database/schema.sql` defines a comprehensive schema including `transactions`, `users`, `accounts`, and `rules`.
- `src/services/db_service.py` provides a `DatabaseService` with methods for initialization, upserting transactions, and recording audit events.
- `src/services/data_service.py` can load from both CSV and DB, but it still falls back to CSV if the DB is empty or missing.
- Deduplication logic exists in `src/services/dedup_service.py` and `csv_to_db_migrator.py`.

### Affected Areas
- `src/services/data_service.py` — Needs to move from CSV-first to DB-first or DB-only.
- `src/ui/pages/import_page.py` — Needs to ensure every import is immediately and correctly synced to DB.
- `src/ui/pages/analytics_page.py` — Should rely exclusively on DB for "Global Overview" and per-bank views.
- `src/csv_to_db_migrator.py` — Needs to be verified as a reliable tool for initial migration of legacy data.
- `src/services/db_service.py` — Might need refined deduplication or bulk insert capabilities.

### Approaches
1. **DB as Primary with CSV Sync** — Maintain CSVs for backward compatibility with Firefly III manual import but use DB for all internal app logic (Analytics, UI).
   - Pros: Safety net (CSVs still exist), works with existing Firefly workflow.
   - Cons: Dual source of truth risk.
   - Effort: Medium

2. **DB as Source of Truth (Pure Persistence)** — Move entirely to SQLite. CSVs are only generated on-demand for export.
   - Pros: Clean architecture, single source of truth, better performance for large datasets.
   - Cons: Requires solid initial migration of all current CSV data.
   - Effort: High

### Recommendation
I recommend **Approach 2 (DB as Source of Truth)**. The project has evolved to a point where managing multiple CSV files is becoming brittle. SQLite provides the transactional integrity needed for financial data. We should use `csv_to_db_migrator.py` to ingest all existing data once, then make the DB the master store.

### Risks
- **Data Loss during Migration**: If the migrator has bugs, we might lose or corrupt historical data.
- **Deduplication Conflicts**: Moving from per-bank CSVs to a unified DB table requires infallible `source_hash` logic to avoid cross-bank collisions or missing legitimate duplicates.

### Ready for Proposal
Yes — I have a clear map of the current DB state and what's needed to make it the primary store.
