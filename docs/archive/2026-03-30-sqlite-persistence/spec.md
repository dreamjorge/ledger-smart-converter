# Specification Delta: SQLite Persistence

## Domain: Persistence

### ADDED Requirements

#### Requirement: DB-First Transaction Loading
The `data_service` MUST query SQLite as the primary source for all transaction data. CSV files SHOULD only be used as a fallback if the database is uninitialized or missing historical data.

#### Scenario: Load transactions for a specific bank
- GIVEN the database is initialized and contains transactions for "santander"
- WHEN `load_transactions` is called for bank "santander"
- THEN the system SHALL execute a SELECT query against the `transactions` table
- AND it SHALL return a DataFrame populated from the database results

#### Requirement: Transactional Import Persistence
The import pipeline MUST ensure that all successfully parsed and categorized transactions are persisted to the database within a single transaction to maintain atomicity.

#### Scenario: Successful bank import persistence
- GIVEN a valid bank statement is uploaded
- WHEN the processing is complete
- THEN the system SHALL insert or replace all transactions in the `transactions` table
- AND it SHALL record an entry in the `imports` table with the result status

### MODIFIED Requirements

#### Requirement: Unique Transaction Identification
The system MUST use a `source_hash` generated from `(bank_id, date, amount, description)` to identify unique transactions.
(Previously: Identified primarily by row index or file name in CSVs).

#### Scenario: Prevent duplicate transaction insertion
- GIVEN a transaction with a specific `source_hash` already exists in the DB
- WHEN an import attempts to insert a transaction with the same `source_hash`
- THEN the system SHALL either skip the insertion or overwrite based on the chosen deduplication strategy

## Domain: Analytics

### ADDED Requirements

#### Requirement: Direct SQL Aggregation
The analytics dashboard MUST use direct SQL queries (or database views) to calculate metrics and trends instead of manual pandas aggregation across multiple DataFrames.

#### Scenario: Calculate categorization stats
- GIVEN the Analytics page is active
- WHEN metrics are requested
- THEN the system SHALL query the `dashboard_metrics` view or equivalent SQL aggregation
- AND it SHALL return the calculated stats (total spent, coverage pct, etc.)

#### Requirement: Unified Cross-Account View
The "Global Overview" MUST be implemented as a single SQL query that aggregates data from all accounts in the `transactions` table.

#### Scenario: View global overview
- GIVEN transactions exist for multiple bank accounts in the DB
- WHEN the user selects "All Accounts"
- THEN the system SHALL execute a query without a `bank_id` filter (or grouping by bank)
- AND it SHALL render the combined data from the entire database

## Success Criteria
- [ ] `data_service.py` functions use SQLite as primary store.
- [ ] Analytics dashboard loads data via SQL queries.
- [ ] No data loss or duplicates after full CSV migration.
- [ ] "Global Overview" correctly aggregates all DB records.
