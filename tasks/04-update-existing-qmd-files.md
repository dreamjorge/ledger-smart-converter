# Task: Update Existing QMD Context Files

**Priority**: High
**Effort**: Medium (2–3 hours total across 4 files)
**Files**: `docs/context/domain.qmd`, `docs/context/services.qmd`, `docs/context/testing.qmd`, `docs/context/ml-categorization.qmd`

---

## Why

These QMD files are the canonical context for agents. Several code changes made in the
`update-md-files` branch are not yet reflected, making the context stale.
Stale QMD = agents re-derive what they could read in seconds.

---

## 1. domain.qmd — `Optional[float]` for amount

**Change**: `amount: float` → `amount: Optional[float]` was merged as a blocking fix.

**Update**: In the `CanonicalTransaction` field table, change:

```diff
-| `amount`      | `float`            | Transaction amount (positive) |
+| `amount`      | `Optional[float]`  | Transaction amount; None allowed (validation rejects None downstream) |
```

Also update the `id` property note:
```markdown
The `id` property guards against `amount=None` by producing an empty string for the
amount component rather than crashing with `TypeError`.
```

---

## 2. services.qmd — Add DatabaseService + Analytics date fix

### 2a. Add a new "Database Service" section

Point to `docs/context/db.qmd` for full detail (avoid duplication), but add a brief entry:

```markdown
### Database Service (see also: `docs/context/db.qmd`)

**File**: `src/services/db_service.py`

**Responsibilities**: SQLite persistence, deduplication via `source_hash`, audit events.

**Key integration point**: `analytics_service.calculate_categorization_stats_from_db()`
queries the DB directly when a `db_path` is available, bypassing CSV loading.
```

### 2b. Update Analytics Service section — date coercion note

The `calculate_categorization_stats()` function now coerces `date` to datetime before
calling `.dt.to_period()`. Add a note:

```markdown
**Note**: `date` column is coerced with `pd.to_datetime(..., errors="coerce")` and rows
with `NaT` are dropped before `year_month` computation. This handles both the CSV path
(raw strings) and the DB path (already datetime objects).
```

---

## 3. testing.qmd — Document `@pytest.mark.slow` pattern

Add a new section "Slow Test Strategy":

```markdown
## Slow Test Strategy

Tests that require sklearn training (3+ min on cold import) are tagged `@pytest.mark.slow`.

### Marked files
- `tests/test_ml_categorizer.py` — 6 tests
- `tests/test_ml_categorizer_normalized.py` — 2 tests

### Running
```bash
pytest -m "not slow" -q      # fast suite, ~34s — use during development
pytest -q                     # full suite — use before PR merge
```

### Marking a test as slow
```python
import pytest
pytestmark = pytest.mark.slow   # marks all tests in file

# or per-test:
@pytest.mark.slow
def test_train_and_predict(): ...
```

### Rules
- Mark any test that: (a) instantiates `TransactionCategorizer`, (b) calls `train_from_csvs()` with real sklearn, or (c) imports sklearn-heavy modules at collection time.
- Do NOT mark tests that use `DummyPipeline` mocks — those are already fast.
```

Also update the CI section to mention `@pytest.mark.slow` usage in `.github/workflows/ci.yml`
(see task 07 — CI should use `-m "not slow"` to stay within time limits).

---

## 4. ml-categorization.qmd — normalized_description integration

### 4a. Add `normalized_description` to training data section

```markdown
**Text column selection** (priority order):
1. `normalized_description` if `LSC_USE_NORMALIZED_TEXT=true` (default) and column exists
2. `description` as fallback

This means `description_normalizer.normalize_description()` is applied at write time
(when transactions are stored) rather than at predict time — improving reproducibility.
```

### 4b. Add `backfill_normalized_descriptions()` note

```markdown
**Backfilling**: For historical transactions without `normalized_description`, run:
```python
db.backfill_normalized_descriptions(normalize_description)
```
This ONLY updates `normalized_description` — `raw_description` is never touched.
```

### 4c. Update `MODEL_DIR` path note

```diff
-MODEL_DIR = Path("config/ml_models")   # relative to CWD
+MODEL_DIR = _load_settings().config_dir / "ml_models"   # absolute, from settings
```

---

## Rendering All Updated Files

```bash
quarto render docs/context/domain.qmd
quarto render docs/context/services.qmd
quarto render docs/context/testing.qmd
quarto render docs/context/ml-categorization.qmd
```

---

## Acceptance Criteria

- [ ] `domain.qmd`: amount type updated, id guard noted
- [ ] `services.qmd`: DatabaseService cross-reference section added, date coercion note in analytics
- [ ] `testing.qmd`: `@pytest.mark.slow` section added with usage examples
- [ ] `ml-categorization.qmd`: normalized_description column selection documented, backfill method noted, MODEL_DIR update noted
- [ ] All 4 `.html` files re-rendered and committed
