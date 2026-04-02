# Proposal: SQLite Persistence

## Intent
Establish SQLite as the primary source of truth for the Ledger Smart Converter, replacing the current CSV-first approach. This will improve data integrity, enable faster cross-account analytics, and provide a more robust foundation for future features like multi-user support.

## Scope

### In Scope
- **DB-First Architecture**: Refactor `data_service.py` to prioritize SQLite for all data loading.
- **Unified Transaction Store**: Migrate all existing CSV data into the unified `transactions` table.
- **Import Integration**: Ensure the import pipeline automatically and transactionally persists new data to SQLite.
- **Schema Hardening**: Verify and enforce the `transactions` schema (unique hashes, proper foreign keys).
- **Global Overview migration**: Refactor `analytics_page.py` to use SQL queries instead of aggregating pandas DataFrames from CSVs.

### Out of Scope
- Migrating to a client-server DB (e.g., PostgreSQL).
- Removing CSV exports (we still need them for Firefly III).
- Full multi-user isolation logic (handled in a separate change).

## Approach
We will implement a "Primary DB" strategy. On app startup, we will ensure the DB is initialized and synced. The `data_service.py` will be the gatekeeper, providing a unified API that queries SQLite. We will use the existing `csv_to_db_migrator.py` logic to perform a one-time migration of any legacy CSV data.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/services/data_service.py` | Modified | Change default loading logic from CSV to DB. |
| `src/services/db_service.py` | Modified | Add bulk insert and refined deduplication methods. |
| `src/ui/pages/analytics_page.py` | Modified | Use DB views or direct SQL for dashboards. |
| `src/ui/pages/import_page.py` | Modified | Tighten DB sync after successful import. |
| `src/database/schema.sql` | Verified | Ensure indexes and constraints are optimal. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Duplicate data | Medium | Rigorous `source_hash` verification during migration. |
| Performance lag on migration | Low | SQLite is fast for our current data scale. |
| Cross-account collision | Low | Unique constraint on `(source_hash, bank_id)` if needed. |

## Rollback Plan
Keep original CSV files in `data/` as backups. If the DB becomes corrupt, we can re-initialize and re-migrate from the CSVs.

## Dependencies
- Existing SQLite schema (`schema.sql`).
- `csv_to_db_migrator.py` utilities.

## Success Criteria
- [ ] All analytics data is pulled from SQLite.
- [ ] New imports are immediately searchable in the DB.
- [ ] "Global Overview" works flawlessly across all bank accounts using direct SQL.
- [ ] No duplicate transactions exist in the unified `transactions` table.
