# Task: Code-Level Enhancements

**Priority**: Low–Medium (mixed)
**Effort**: Varies per item
**Files**: See per-item

---

## Overview

These are code improvements identified during the code review and test analysis.
None are blocking, but they reduce technical debt and improve reliability.

---

## Item 1: `ml_categorizer.py` — Warm sklearn on background thread (Medium)

**Problem**: `ML_ENGINE = get_ml_engine()` in `web_app.py` (line 104) blocks the
Streamlit startup while sklearn loads (~3 min on cold machine). The UI shows
"Running get_ml_engine()" with no progress indicator.

**Fix**: Load the ML engine in a background thread so the rest of the UI initializes:

```python
import threading

_ml_engine = None
_ml_lock = threading.Lock()

def get_ml_engine():
    global _ml_engine
    with _ml_lock:
        if _ml_engine is None:
            engine = ml.TransactionCategorizer()
            if engine.load_model():
                _ml_engine = engine
            else:
                ml.train_global_model()
                engine.load_model()
                _ml_engine = engine
    return _ml_engine

# Start background preload at import time
threading.Thread(target=get_ml_engine, daemon=True).start()
```

Then in `web_app.py`, remove `ML_ENGINE = get_ml_engine()` from module level
and call `get_ml_engine()` lazily inside functions that need it.

**Files**: `src/web_app.py`

---

## Item 2: `description_normalizer.py` — Move hardcoded rules to config (Low)

**Problem**: Abbreviation expansions and accent restorations are hardcoded in
`description_normalizer.py`. As the number of banks and merchants grows, these lists
will need frequent editing in Python code.

**Fix**: Move the dictionaries to a new `config/normalizer_rules.yml` section:

```yaml
normalizer:
  abbreviations:
    "MERPAGO": "MercadoPago"
    "WM": "Walmart"
    # ...
  accent_map:
    "BANO": "BAÑO"
    # ...
```

Load them once at module init via `settings.py`. This makes merchant additions a
config-file edit, not a code change — following the same safe-rules pattern.

**Files**: `src/description_normalizer.py`, `config/rules.yml` or new `config/normalizer_rules.yml`

---

## Item 3: `flet_prototype.py` — Clarify status and path (Low)

**Problem**: `src/flet_prototype.py` and `scripts/run_flet.ps1` exist without clear
documentation of whether Flet is the future direction or an experiment. AGENTS.md
and CLAUDE.md are silent about it.

**Fix**:
1. Add a comment at the top of `flet_prototype.py`: `# STATUS: prototype — not production`
2. Add to `CLAUDE.md` under Roadmap: `**Experimental**: Flet UI prototype (`src/flet_prototype.py`, `scripts/run_flet.ps1`) — potential replacement for Streamlit, not yet feature-complete`
3. Add a task entry in `docs/plan_mejoras.md` for the Streamlit → Flet migration decision

**Files**: `src/flet_prototype.py`, `CLAUDE.md`, `docs/plan_mejoras.md`

---

## Item 4: `CHANGES.md` — Update to current state (Low)

**Problem**: `CHANGES.md` last entry is dated 2026-02-06. Multiple significant
changes were made in March 2026 (SQLite, normalization, account mapping, Flet prototype,
blocking bug fixes in the update-md-files branch).

**Fix**: Add an entry:

```markdown
## 2026-03-16

### Added
- SQLite persistence via `DatabaseService` and `db_pipeline.py`
- Description normalization via `description_normalizer.py`
- Account canonical mapping via `account_mapping.py` + `config/accounts.yml`
- Flet UI prototype (`src/flet_prototype.py`)
- `@pytest.mark.slow` marker for ML training tests

### Fixed
- `CanonicalTransaction.amount` now `Optional[float]` — fixes crash when amount is None
- `analytics_service`: date column coerced to datetime before `.dt.to_period()`
- `db_service.backfill_normalized_descriptions`: no longer overwrites `raw_description`
- `ml_categorizer.MODEL_DIR`: now uses `settings.config_dir` (absolute path)
- `db_service.record_audit_event`: new test coverage added
```

**Files**: `CHANGES.md`

---

## Item 5: `healthcheck.py` — Add DB connectivity check (Medium)

**Problem**: `healthcheck.py` validates Tesseract, config files, and environment
settings, but does not verify that the SQLite DB can be opened and queried.

**Fix**: Add a DB health check:

```python
def check_db():
    from services.db_service import DatabaseService
    db = DatabaseService()
    try:
        count = db.fetch_one("SELECT COUNT(*) AS c FROM transactions")
        return True, f"DB OK — {count['c']} transactions"
    except Exception as e:
        return False, f"DB error: {e}"
```

**Files**: `src/healthcheck.py`

---

## Item 6: `csv_to_db_migrator.py` — Skip filter should also skip `unknown_` files (Low)

**Problem**: The migrator skips files with `"firefly"` in the name to avoid
re-importing generated exports. But `unknown_santander_likeu.csv` and
`suggestions_*.csv` are also generated files that should be skipped.

**Fix**: Expand the skip filter:

```python
SKIP_PATTERNS = ["firefly", "unknown_", "suggestions_"]

def _should_skip(path: Path) -> bool:
    return any(p in path.name for p in SKIP_PATTERNS)
```

**Files**: `src/csv_to_db_migrator.py`, `tests/test_csv_to_db_migrator.py`

---

## Acceptance Criteria (per item)

- [ ] Item 1: ML engine loads in background; web app shows UI immediately
- [ ] Item 2: Normalization rules in config (or at minimum a YAML schema designed)
- [ ] Item 3: Flet prototype status documented in at least CLAUDE.md
- [ ] Item 4: CHANGES.md updated with March 2026 entries
- [ ] Item 5: Healthcheck includes DB connectivity test
- [ ] Item 6: Migrator skips `unknown_` and `suggestions_` files; test added
