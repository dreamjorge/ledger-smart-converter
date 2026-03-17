# Task: Create docs/context/db.qmd

**Priority**: High
**Effort**: Medium (1–2 hours)
**Files**: `docs/context/db.qmd` (new), `docs/context/db.html` (rendered)

---

## Why

There is no QMD context file for the SQLite persistence layer, which is now a core part
of the system. Any agent working on `db_service.py`, `db_pipeline.py`,
`csv_to_db_migrator.py`, or `schema.sql` has no token-efficient context to read — it must
read the raw source files. This is the highest-priority gap in the context system.

---

## Sections to Include

Use the same format as the other QMD files (see `docs/context/services.qmd` as a template).

### Section 1: Purpose

One paragraph: SQLite as the canonical persistence store, replacing CSV-only storage.
Mention `data/ledger.db`, the schema, and the pipeline.

### Section 2: Schema Overview

Document the 4 main tables:

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `transactions` | `id`, `source_hash`, `date`, `amount`, `description`, `raw_description`, `normalized_description`, `bank_id`, `account_id`, `canonical_account_id`, `transaction_type`, `destination_name`, `category`, `tags`, `import_id` | Main fact table |
| `accounts` | `account_id`, `display_name`, `type`, `bank_id`, `closing_day`, `currency` | Account master data |
| `imports` | `import_id`, `bank_id`, `source_file`, `processed_at`, `status`, `row_count`, `error` | Import run log |
| `audit_events` | `id`, `event_type`, `entity_type`, `entity_id`, `payload_json`, `created_at` | Audit trail |

### Section 3: DatabaseService API

Document each public method with signature + one-line description:

```python
initialize() -> None
# Applies schema.sql, runs column migrations via _ensure_transactions_columns()

upsert_account(account_id, display_name, account_type, bank_id, closing_day, currency) -> None

record_import(bank_id, source_file, status, row_count, error) -> int
# Returns import_id

update_import_status(import_id, status, row_count, error) -> None

insert_transaction(txn: Dict, import_id) -> bool
# INSERT OR IGNORE on source_hash — returns True if inserted, False if duplicate

backfill_normalized_descriptions(normalizer: Callable) -> int
# Only updates normalized_description, never overwrites raw_description

record_audit_event(event_type, entity_type, entity_id, payload) -> int

fetch_one(query, params) -> Optional[Dict]
fetch_all(query, params) -> List[Dict]
```

### Section 4: Deduplication Strategy

Explain `source_hash` (SHA-256 of `bank_id|source_file|date|amount|description`).
`INSERT OR IGNORE` means safe to re-run imports without duplicates.

### Section 5: Pipeline

```
CSV files → csv_to_db_migrator.py → DatabaseService.insert_transaction()
                                  → DatabaseService.record_import()

Trigger: scripts/run_db_pipeline.py → src/db_pipeline.py
```

### Section 6: Safe Patterns

- **Never** issue raw `UPDATE` on `raw_description` unless you are the initial importer
- Backfill ONLY updates `normalized_description`
- `_ensure_transactions_columns()` adds columns via `ALTER TABLE` — safe to re-run
- All writes inside `with self._connect() as conn:` (auto-rollback on error)

### Section 7: Migration Notes

Document `csv_to_db_migrator.py` safeguards:
- Skips files whose name contains `"firefly"` (avoids re-importing generated exports)
- Checks `imports` table for `source_file` to skip already-processed files
- Calls `upsert_account()` before inserting transactions

### Section 8: Audit Trail Usage

```python
db.record_audit_event(
    event_type="import_complete",
    entity_type="import",
    entity_id=str(import_id),
    payload={"row_count": 42, "bank_id": "santander_likeu"},
)
```

---

## Rendering

After creating the `.qmd` file:
```bash
quarto render docs/context/db.qmd
```
Commit both `.qmd` and `.html`.

---

## Acceptance Criteria

- [ ] `docs/context/db.qmd` exists and covers all 8 sections
- [ ] All `DatabaseService` public methods documented with signatures
- [ ] Schema table documented
- [ ] Safety rules documented (no raw_description overwrite, etc.)
- [ ] `docs/context/db.html` rendered and committed
- [ ] `AGENTS.md` QMD routing table updated (see task 02)
- [ ] `CLAUDE.md` header table updated (see task 01)
