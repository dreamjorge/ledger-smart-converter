# Tasks: SQLite Persistence

## Phase 1: Foundation (Core Services)

- [x] 1.1 Add `insert_transactions_batch` to `src/services/db_service.py` using a single transaction for atomicity.
- [x] 1.2 Update `src/services/data_service.py` to make `prefer_db=True` the default in all loading functions.
- [x] 1.3 Implement `get_unified_dashboard_stats` in `src/services/analytics_service.py` using raw SQL aggregations.
- [x] 1.4 Refactor `calculate_categorization_stats` in `src/services/analytics_service.py` to optionally use the DB view.

## Phase 2: Implementation (Analytics Refactor)

- [x] 2.1 Update `src/ui/pages/analytics_page.py` to use the new unified stats service instead of pandas-based aggregation.
- [x] 2.2 Ensure "Global Overview" tab in UI pulls data directly from the unified SQL query.
- [x] 2.3 Add "Sync Historical Data" action to `src/ui/pages/settings_page.py` to trigger `csv_to_db_migrator`.

## Phase 3: Wiring (Import Pipeline)

- [x] 3.1 Modify `src/ui/pages/import_page.py` to force a DB sync immediately after a successful CSV export.
- [x] 3.2 Update the import process to use `insert_transactions_batch` for the final persistence step.

## Phase 4: Testing & Verification

- [x] 4.1 Write unit tests for `insert_transactions_batch` verifying unique constraint handling.
- [x] 4.2 Verify migration of existing legacy CSVs into the unified `transactions` table.
- [x] 4.3 Compare Analytics dashboard metrics between DB and legacy CSV sources to ensure parity.
- [x] 4.4 Perform E2E test of the full workflow: Import -> Auto-Sync -> View in Dashboard.
