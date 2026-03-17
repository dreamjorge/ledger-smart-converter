# Task: Update CLAUDE.md

**Priority**: Medium
**Effort**: Small (30 min)
**Files**: `CLAUDE.md`

---

## Why

CLAUDE.md is the first file Claude Code reads in every session. It currently reflects the
pre-SQLite era of the project. Several major features added since then (SQLite persistence,
description normalization, DB pipeline, account mapping) are absent, which leads agents to
miss the DB layer entirely and re-derive it from source.

---

## Specific Changes

### 1. Update Stack line (line 4)

```diff
-**Stack**: Python 3.8+, Streamlit, sklearn, pytest
+**Stack**: Python 3.8+, Streamlit, sklearn, SQLite, pytest
```

### 2. Add missing files to "Files I'll Need Most" section

```markdown
**To work with the database**: `src/services/db_service.py`, `src/database/schema.sql`
**To run the full ETL pipeline**: `scripts/run_db_pipeline.py`, `src/db_pipeline.py`
**To migrate CSV history to DB**: `src/csv_to_db_migrator.py`
**To normalize descriptions**: `src/description_normalizer.py`
**To map accounts**: `src/account_mapping.py`, `config/accounts.yml`
```

### 3. Add "Run DB Pipeline" common request pattern

```markdown
### "Run or debug the DB pipeline"
1. Check `src/db_pipeline.py` for the ETL entry point
2. Run `python scripts/run_db_pipeline.py`
3. Inspect `src/csv_to_db_migrator.py` for the CSV → SQLite migration logic
4. Read `docs/context/db.qmd` for the full DB layer context  ← (create this file; see task 03)
```

### 4. Update Roadmap Context section

```diff
-**Recently completed**: Validation layer, service architecture, safe rules workflow, CI
-**Next up**: SQLite persistence, account unification, hash-based deduplication
+**Recently completed**: SQLite persistence, description normalization, account mapping, DB pipeline, Flet UI prototype
+**Next up**: Firefly API sync, automated monthly reports, Flet UI to replace Streamlit
```

### 5. Add `@pytest.mark.slow` to Testing Strategy section

```markdown
**Slow tests**: ML training tests are marked `@pytest.mark.slow`.
**Fast suite**: `pytest -m "not slow" -q` (skips 8 ML tests, ~34s)
**Full suite**: `pytest -q` (includes ML training, ~55+ min on slow machines)
```

### 6. Add DB to Architecture layers description

```diff
 ### Architecture is Layered
 - **Domain** models enforce validation (`src/domain/`)
 - **Services** contain business logic (`src/services/`)
 - **UI** is presentation only (`src/ui/pages/`)
 - **Importers** are bank-specific parsers (`src/import_*.py`)
+- **Database** is persistence (`src/services/db_service.py`, `src/database/schema.sql`)
```

### 7. Add db.qmd to context routing table in CLAUDE.md header

```markdown
| Database/Persistence | `docs/context/db.qmd` | `src/services/db_service.py`, `src/db_pipeline.py`, `src/csv_to_db_migrator.py` |
```

---

## Acceptance Criteria

- [ ] Stack line mentions SQLite
- [ ] DB-related files listed in "Files I'll Need Most"
- [ ] "Run DB Pipeline" pattern exists in Common Request Patterns
- [ ] Roadmap Context reflects current state
- [ ] `@pytest.mark.slow` strategy documented
- [ ] `docs/context/db.qmd` referenced (can reference before it exists)
