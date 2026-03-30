# Design: SQLite Persistence

## Technical Approach
We will transition the application from a CSV-first approach to a DB-first architecture where SQLite is the primary source of truth. The system will leverage the existing `DatabaseService` and `csv_to_db_migrator` to ensure all data is unified in the `transactions` table. Analytics will be refactored to use SQL aggregations for better performance and consistency across bank accounts.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|----------|--------|-------------------------|-----------|
| Primary Data Store | SQLite | CSV Files | Transactional integrity, faster queries, and unified data across accounts. |
| Loading Strategy | DB-First with CSV Fallback | DB-Only | Fallback ensures historical data is not lost if the DB is cleared, but DB is always preferred. |
| Analytics Engine | SQL Aggregation | pandas groupby on DataFrames | SQL is significantly faster for cross-bank aggregations and avoids high memory usage for large datasets. |
| Import Workflow | Auto-Sync to DB | Manual Import Step | Seamless user experience; data is available for analysis immediately after import. |

## Data Flow

    [Input File] ──→ [Bank Importer] ──→ [CSV Export] ──→ [Database Sync] ──→ [SQLite DB]
                                                                                │
    [Analytics UI] ←── [Analytics Service] ←── [SQL Queries / Views] ←──────────┘

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/services/data_service.py` | Modify | Update `load_transactions` to default to `prefer_db=True`. |
| `src/services/db_service.py` | Modify | Add `insert_transactions_batch` for performance. |
| `src/services/analytics_service.py` | Modify | Refactor calculation functions to use direct SQL via `DatabaseService`. |
| `src/ui/pages/import_page.py` | Modify | Ensure `migrate_csvs_to_db_with_dedup` is called after every successful run. |
| `src/ui/pages/analytics_page.py` | Modify | Simplify data loading logic by requesting unified stats from the service. |

## Interfaces / Contracts

The `AnalyticsService` will expose a new method for unified cross-account stats:

```python
# src/services/analytics_service.py
def get_unified_dashboard_stats(db_path: Path) -> Dict[str, Any]:
    """Calculate stats for ALL accounts using direct SQL."""
    # SELECT SUM(amount), COUNT(*), etc. FROM transactions ...
```

The `data_service` will prioritize the database:

```python
# src/services/data_service.py
def load_transactions(bank_id: str, prefer_db: bool = True, ...) -> pd.DataFrame:
    # Always try DB first if prefer_db is True (default)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `db_service.insert_transactions_batch` | Test batch insertion with mock data and unique hash constraints. |
| Integration | `data_service.load_transactions` | Verify data is correctly pulled from DB when available vs CSV fallback. |
| Integration | `analytics_service` SQL | Compare SQL-calculated results with known pandas-calculated benchmarks. |

## Migration / Rollout
A one-time migration will be triggered on app startup (or via a "Sync Historical Data" button) using the `csv_to_db_migrator`. This will ingest all files matching `data/**/firefly*.csv`.

## Open Questions
- [ ] Should we delete CSV files after migration? (Decision: No, keep them as secondary backups for Firefly III).
- [ ] Do we need a "Refresh DB from CSV" button in the UI? (Decision: Yes, in Settings).
