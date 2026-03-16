# Task: Update Existing Skills

**Priority**: Medium
**Effort**: Small (45 min total)
**Files**: `skills/testing/SKILL.md`, `skills/analytics/SKILL.md`, `skills/categorization/SKILL.md`

---

## Why

Three existing skills need small updates to reflect the current state of the codebase.
None require full rewrites — just targeted additions.

---

## 1. skills/testing/SKILL.md — Add `@pytest.mark.slow`

### What to add

After the existing "Running tests" section, add:

```markdown
### Slow vs Fast Suite

ML training tests are tagged `@pytest.mark.slow` and take 3+ min on cold startup.

```bash
pytest -m "not slow" -q   # development loop (~34s)
pytest -q                  # full suite before merge
```

When writing new tests that instantiate `TransactionCategorizer` with real sklearn:
- Tag the test file with `pytestmark = pytest.mark.slow`
- If using `DummyPipeline` mock — no tag needed, it's fast
```

---

## 2. skills/analytics/SKILL.md — Add DB path

### What to add

In the "Data Sources" or equivalent section:

```markdown
### Two Analytics Paths

| Path | Function | When Used |
|------|----------|-----------|
| **CSV path** | `calculate_categorization_stats(df)` | Legacy, when no DB exists |
| **DB path** | `calculate_categorization_stats_from_db(db_path)` | Primary, when `data/ledger.db` exists |

The DB path pre-converts `date` to datetime before passing to the shared function.
The CSV path now also coerces `date` inline — both paths are safe with string dates.
```

Also add to the "Debugging analytics issues" section:
```markdown
- If monthly trends are empty, check that `date` column contains datetime objects
  (not raw strings). The function now handles both, but confirm with
  `df["date"].dtype` in a REPL.
```

---

## 3. skills/categorization/SKILL.md — Add normalized_description awareness

### What to add

In the "How ML training works" or equivalent section:

```markdown
### Normalized Description Feature

Training prefers `normalized_description` over raw `description` when:
- `LSC_USE_NORMALIZED_TEXT=true` (default)
- The column exists in the training CSV

At prediction time, `normalize_description(text)` is applied to the input before
passing to the sklearn pipeline. This means the model sees the same cleaned text
at both train and predict time.

To disable: set `LSC_USE_NORMALIZED_TEXT=false` in `.env`.
```

---

## Acceptance Criteria

- [ ] `skills/testing/SKILL.md`: `@pytest.mark.slow` usage documented
- [ ] `skills/analytics/SKILL.md`: CSV vs DB paths documented, date coercion noted
- [ ] `skills/categorization/SKILL.md`: normalized_description workflow documented
