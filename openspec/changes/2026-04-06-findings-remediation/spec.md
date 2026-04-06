# Spec: Findings Remediation

---

## Domain: Deduplication (F1 + F3)

### Requirement: Unified Source Hash

The system MUST use a single canonical hash function to identify unique transactions. `CanonicalTransaction.id` and `build_source_hash()` MUST produce identical output for the same transaction data.

#### Scenario: Hash consistency between domain object and DB service

- GIVEN a transaction with known fields (bank_id, date, amount, description, canonical_account_id)
- WHEN `CanonicalTransaction.id` and `build_source_hash()` are called with equivalent data
- THEN both MUST return the same SHA-256 hex string

#### Scenario: Reimport from different absolute path does not create duplicate

- GIVEN a transaction already persisted with `source_file = "/old/path/file.csv"`
- WHEN the same transaction is imported again with `source_file = "/new/path/file.csv"`
- THEN `INSERT OR IGNORE` MUST skip the row (same hash → same dedup key)
- AND the DB MUST still contain exactly one row for that transaction

#### Scenario: Different files with same filename but different content are distinct

- GIVEN two files named `firefly_santander_likeu.csv` with different transaction data
- WHEN both are imported
- THEN the transactions MUST receive different hashes (content fields differ)

### Requirement: Path-Independent Hash

The hash MUST NOT include the absolute filesystem path of the source file. Only the filename (basename) MAY be included if source file is part of the hash inputs.

#### Scenario: Moving project directory does not invalidate dedup

- GIVEN transactions imported from `C:\Users\A\data\file.csv`
- WHEN the project is moved and reimported from `C:\Users\B\data\file.csv`
- THEN the system MUST detect them as duplicates

---

## Domain: Categorization (F2)

### Requirement: Restaurants Rule MUST NOT Match Non-Restaurant Prefixes

The `Restaurants` categorization rule MUST only match strings where "rest" appears as a standalone word prefix for known restaurant patterns, not as a substring of unrelated words.

#### Scenario: Known restaurant patterns still categorize correctly

- GIVEN a transaction description "Rest Alabim Alabam"
- WHEN classified against rules
- THEN the expense MUST be `Expenses:Food:Restaurants`

#### Scenario: "Restore" does not match Restaurants

- GIVEN a transaction description "Restore Electronics"
- WHEN classified against rules
- THEN the expense MUST NOT be `Expenses:Food:Restaurants`
- AND it SHOULD fall back to `Expenses:Other:Uncategorized`

#### Scenario: "Restroom" does not match Restaurants

- GIVEN a transaction description "Restroom Supplies Co"
- WHEN classified against rules
- THEN the expense MUST NOT be `Expenses:Food:Restaurants`

---

## Domain: Observability (F7)

### Requirement: Statement Period Parse Failures MUST Be Logged

When `get_statement_period()` cannot parse the transaction date, the system MUST emit a WARNING-level log entry. The function MUST NOT fail silently.

#### Scenario: Invalid date string triggers warning

- GIVEN a transaction with `date = "not-a-date"`
- WHEN `get_statement_period("not-a-date", 15)` is called
- THEN the function MUST return `""` (empty string, existing behavior)
- AND a WARNING MUST be logged containing the invalid date value

#### Scenario: Valid date produces no warning

- GIVEN a transaction with `date = "2026-01-10"`
- WHEN `get_statement_period("2026-01-10", 15)` is called
- THEN the function MUST return `"2026-01"`
- AND NO warning MUST be logged

#### Scenario: Pipeline logs when period is missing

- GIVEN a transaction whose date cannot be parsed
- WHEN `ImportPipelineService.process_transactions()` processes it
- THEN a WARNING MUST be logged indicating the transaction ID and the missing period
- AND the transaction MUST still be processed (non-fatal)

---

## Success Criteria

- [ ] `CanonicalTransaction.id == build_source_hash(...)` for identical transaction data
- [ ] Reimport from different path → 0 new rows inserted
- [ ] "Restore Electronics" → `Expenses:Other:Uncategorized`
- [ ] "Restroom Supplies" → `Expenses:Other:Uncategorized`
- [ ] "Rest Alabim Alabam" → `Expenses:Food:Restaurants` (no regression)
- [ ] `get_statement_period("bad-date", 15)` → emits WARNING log
- [ ] `pytest -m "not slow" -q` → 0 failures, coverage ≥ 80%
