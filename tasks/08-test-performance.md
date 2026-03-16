# Task: Investigate & Reduce Test Suite Runtime

**Priority**: Medium
**Effort**: Medium (2–4 hours)
**Files**: `tests/`, `pytest.ini`, potentially `src/`

---

## Context

The non-slow test suite (`pytest -m "not slow"`) currently runs in **39 minutes** for
546 tests — an average of **~4.3 seconds per test**. This is abnormally slow for Python
unit tests that don't involve sklearn training.

The `@pytest.mark.slow` tag reduced the worst offenders, but something else is
causing widespread slowness across the other 546 tests.

---

## Step 1: Profile — Find the bottlenecks

Run with `--durations` to identify the 30 slowest tests:

```bash
pytest -m "not slow" --durations=30 -q 2>&1 | tail -50
```

Expected culprits:
- **Streamlit UI tests** — Streamlit imports at collection time can add 10–30s
- **Flet prototype tests** — if any exist, Flet is a heavy import
- **PDF/OCR tests** — pdf2image, Pillow, pytesseract startup
- **Integration tests** — tests that spin up full import pipeline with real CSV parsing

---

## Step 2: Mark slow-but-not-ML tests

Based on `--durations` output, apply `@pytest.mark.slow` (or a new `@pytest.mark.integration`)
to any test that consistently takes >5s. Candidates:

- `tests/test_ui_pages_imports.py` — likely imports Streamlit
- `tests/test_web_app_config.py` — likely imports the full Streamlit app
- `tests/test_pdf_utils.py` — OCR dependencies
- `tests/test_import_hsbc_cfdi_firefly.py` / `test_import_likeu_firefly.py` — XML/XLSX parsing

---

## Step 3: Check conftest.py fixtures for expensive setup

Read `tests/conftest.py` for any session-scoped fixtures that:
- Load the full Streamlit app
- Build large DataFrames
- Do file I/O

Move expensive setup to `scope="session"` if it's done repeatedly at `scope="function"`.

---

## Step 4: Consider `pytest-xdist` for parallelism

```bash
pip install pytest-xdist
pytest -m "not slow" -n auto -q
```

`-n auto` uses all available CPU cores. For I/O-bound tests this can give 2–4× speedup.

**Caveat**: Tests must be independent (no shared state, no shared temp files).
Check for any tests that write to `data/` or `config/` without `tmp_path`.

---

## Step 5: Check for test isolation issues

Some tests may be leaving behind state that causes subsequent tests to be slow.
Run with `-p no:randomly` to disable random ordering (if pytest-randomly is installed)
and check if specific orderings are slower.

---

## Target Outcome

| Scenario | Current | Target |
|----------|---------|--------|
| Fast suite (`-m "not slow"`) | 39 min | < 5 min |
| PR validation in CI | 39+ min | < 10 min |
| Development loop (subset) | ~34s per module | Unchanged |

---

## Acceptance Criteria

- [ ] `--durations=30` run completed and top 30 slowest tests identified
- [ ] Slow non-ML tests tagged (with `@pytest.mark.slow` or new `@pytest.mark.integration`)
- [ ] Fast suite (`-m "not slow"`) runs in under 5 minutes
- [ ] CI pipeline uses the fast suite (see task 07)
