# Project Architecture Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the project toward cleaner service boundaries, DB-first runtime behavior, normalized configuration ownership, and up-to-date architecture documentation without breaking current import and analytics flows.

**Architecture:** The plan keeps working importer parsers intact while moving orchestration responsibilities into cleaner service seams. It treats SQLite as the preferred operational source, preserves CSV compatibility as fallback/interchange, and updates the documentation layer as part of the refactor rather than after it.

**Tech Stack:** Python 3.8+, pytest, pandas, sqlite3, Streamlit, YAML, Quarto/QMD docs

---

### Task 1: Baseline Architecture Snapshot

**Files:**
- Modify: `docs/project-index.qmd`
- Modify: `docs/plan_mejoras.md`
- Modify: `docs/context/services.qmd`
- Modify: `docs/context/db.qmd`
- Test: `python -m pytest --collect-only -q`

**Step 1: Capture the current system facts**

Run: `python -m pytest --collect-only -q`
Expected: suite collects successfully; record the current count and major test groups.

**Step 2: Update stale architecture statements**

Edit the docs above so they no longer describe delivered DB/account/export capabilities as pending.

**Step 3: Record current canonical runtime model**

Document:
- DB-first read behavior
- CSV fallback behavior
- current test count
- current service responsibilities

**Step 4: Verify docs remain coherent**

Run: `rg -n "pendiente|planned|Next|550 tests|554 tests" docs/project-index.qmd docs/plan_mejoras.md docs/context/services.qmd docs/context/db.qmd`
Expected: no obviously stale claims about already delivered architecture.

**Step 5: Commit**

```bash
git add docs/project-index.qmd docs/plan_mejoras.md docs/context/services.qmd docs/context/db.qmd
git commit -m "docs: refresh architecture baseline"
```

### Task 2: Add Import Orchestration Seam Tests

**Files:**
- Modify: `tests/test_generic_importer.py`
- Modify: `tests/test_generic_importer_branches.py`
- Test: `tests/test_generic_importer.py`
- Test: `tests/test_generic_importer_branches.py`

**Step 1: Write failing tests for orchestration seams**

Add tests that isolate and assert:
- parser selection behavior
- normalized-description enrichment path
- account resolution invocation
- strict-mode validation handling

**Step 2: Run targeted tests to confirm coverage gaps**

Run: `python -m pytest tests/test_generic_importer.py tests/test_generic_importer_branches.py -v`
Expected: new tests fail before refactor.

**Step 3: Refine tests around current observable behavior**

Keep the tests focused on outcomes and collaborator boundaries, not implementation trivia.

**Step 4: Re-run targeted tests**

Run: `python -m pytest tests/test_generic_importer.py tests/test_generic_importer_branches.py -v`
Expected: failing tests are stable and clearly express the desired seam.

**Step 5: Commit**

```bash
git add tests/test_generic_importer.py tests/test_generic_importer_branches.py
git commit -m "test: add importer orchestration seam coverage"
```

### Task 3: Extract Import Enrichment Pipeline

**Files:**
- Create: `src/services/import_pipeline_service.py`
- Modify: `src/generic_importer.py`
- Modify: `docs/context/services.qmd`
- Test: `tests/test_generic_importer.py`

**Step 1: Write the failing test for extracted enrichment behavior**

Add or refine a test asserting that enrichment/categorization behavior remains stable when routed through a dedicated service helper.

**Step 2: Run the focused test**

Run: `python -m pytest tests/test_generic_importer.py -v`
Expected: FAIL until the new service exists and is wired.

**Step 3: Write minimal implementation**

Create `src/services/import_pipeline_service.py` with focused functions for:
- building canonical transaction fields
- validation pass
- categorization/tag assembly
- row shaping for downstream output/persistence

Update `src/generic_importer.py` so it delegates these responsibilities instead of owning them inline.

**Step 4: Run importer tests**

Run: `python -m pytest tests/test_generic_importer.py tests/test_generic_importer_branches.py tests/test_generic_importer_normalized.py -v`
Expected: PASS

**Step 5: Update service docs**

Add the new service module and function responsibilities to `docs/context/services.qmd`.

**Step 6: Commit**

```bash
git add src/services/import_pipeline_service.py src/generic_importer.py docs/context/services.qmd tests/test_generic_importer.py
git commit -m "refactor: extract importer enrichment pipeline"
```

### Task 4: Add Data Source Contract Tests

**Files:**
- Modify: `tests/test_data_service.py`
- Modify: `tests/test_analytics_service_db.py`
- Test: `tests/test_data_service.py`
- Test: `tests/test_analytics_service_db.py`

**Step 1: Write failing tests for DB-first and fallback behavior**

Cover:
- DB preferred when rows exist
- CSV fallback when DB missing
- CSV fallback when DB exists but has no rows for a bank
- handling of unknown bank IDs

**Step 2: Run targeted tests**

Run: `python -m pytest tests/test_data_service.py tests/test_analytics_service_db.py -v`
Expected: new tests fail on current gaps or assumptions.

**Step 3: Tighten test assertions around service contracts**

Assert outputs and source-selection behavior, not internal implementation details.

**Step 4: Re-run targeted tests**

Run: `python -m pytest tests/test_data_service.py tests/test_analytics_service_db.py -v`
Expected: failures clearly describe the intended contract.

**Step 5: Commit**

```bash
git add tests/test_data_service.py tests/test_analytics_service_db.py
git commit -m "test: define data source service contracts"
```

### Task 5: Normalize Data Source Resolution

**Files:**
- Modify: `src/services/data_service.py`
- Modify: `src/settings.py`
- Modify: `config/accounts.yml`
- Modify: `docs/context/services.qmd`
- Modify: `docs/context/db.qmd`
- Test: `tests/test_data_service.py`

**Step 1: Write the failing test for config-driven or metadata-driven path resolution**

Add a focused test that demonstrates the desired replacement for rigid static path assumptions.

**Step 2: Run the targeted test**

Run: `python -m pytest tests/test_data_service.py -v`
Expected: FAIL before implementation.

**Step 3: Write minimal implementation**

Refactor `data_service` so:
- DB-first remains the default
- CSV fallback resolution is derived from config/settings metadata where practical
- bank aliases remain supported without hardcoding scattered maps

If `accounts.yml` is insufficient, add only the minimum metadata needed to support this contract.

**Step 4: Run service tests**

Run: `python -m pytest tests/test_data_service.py tests/test_import_service.py tests/test_db_pipeline.py -v`
Expected: PASS

**Step 5: Update docs**

Document the new resolution behavior in the affected QMD files.

**Step 6: Commit**

```bash
git add src/services/data_service.py src/settings.py config/accounts.yml docs/context/services.qmd docs/context/db.qmd tests/test_data_service.py
git commit -m "refactor: normalize transaction source resolution"
```

### Task 6: Define Configuration Ownership

**Files:**
- Modify: `config/rules.yml`
- Modify: `config/accounts.yml`
- Modify: `docs/context/importers.qmd`
- Modify: `docs/context/services.qmd`
- Modify: `docs/project-index.qmd`
- Test: `tests/test_account_mapping.py`
- Test: `tests/test_generic_importer.py`

**Step 1: Write failing tests for config contract expectations**

Add tests around account-resolution and importer config lookups that encode the intended ownership split.

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_account_mapping.py tests/test_generic_importer.py -v`
Expected: FAIL until config expectations are aligned.

**Step 3: Write minimal implementation**

Clarify and enforce:
- what bank/import settings stay in `rules.yml`
- what canonical account metadata lives in `accounts.yml`
- which values are internal IDs vs display names

Use compatibility adapters if needed to avoid broad breakage.

**Step 4: Run tests**

Run: `python -m pytest tests/test_account_mapping.py tests/test_generic_importer.py tests/test_import_service.py -v`
Expected: PASS

**Step 5: Update docs**

Refresh importer/service/project QMD content to reflect the final config contract.

**Step 6: Commit**

```bash
git add config/rules.yml config/accounts.yml docs/context/importers.qmd docs/context/services.qmd docs/project-index.qmd tests/test_account_mapping.py tests/test_generic_importer.py
git commit -m "refactor: define canonical configuration ownership"
```

### Task 7: Add Analytics Input Normalization Tests

**Files:**
- Modify: `tests/test_analytics_service.py`
- Modify: `tests/test_analytics_service_db.py`
- Test: `tests/test_analytics_service.py`
- Test: `tests/test_analytics_service_db.py`

**Step 1: Write failing tests for normalized analytics inputs**

Cover:
- date coercion behavior
- missing type/category fields
- consistent output across DB and CSV-derived dataframes

**Step 2: Run targeted tests**

Run: `python -m pytest tests/test_analytics_service.py tests/test_analytics_service_db.py -v`
Expected: FAIL where normalization assumptions are implicit.

**Step 3: Rework tests until they encode one stable analytics contract**

Make sure the tests describe the service input/output boundary clearly.

**Step 4: Re-run targeted tests**

Run: `python -m pytest tests/test_analytics_service.py tests/test_analytics_service_db.py -v`
Expected: failing tests are stable and actionable.

**Step 5: Commit**

```bash
git add tests/test_analytics_service.py tests/test_analytics_service_db.py
git commit -m "test: define analytics input normalization contracts"
```

### Task 8: Refactor Analytics Normalization Boundary

**Files:**
- Modify: `src/services/analytics_service.py`
- Modify: `src/services/data_service.py`
- Modify: `docs/context/services.qmd`
- Modify: `docs/context/ui.qmd`
- Test: `tests/test_analytics_service.py`
- Test: `tests/test_analytics_service_db.py`

**Step 1: Write the failing test for the normalization helper**

Add a test for a dedicated normalization boundary or helper used before aggregation.

**Step 2: Run the focused test**

Run: `python -m pytest tests/test_analytics_service.py -v`
Expected: FAIL until implementation exists.

**Step 3: Write minimal implementation**

Refactor analytics so:
- input normalization happens once
- aggregation code consumes a stable shape
- DB and CSV-derived frames behave consistently

**Step 4: Run analytics tests**

Run: `python -m pytest tests/test_analytics_service.py tests/test_analytics_service_db.py tests/test_ui_analytics_components.py -v`
Expected: PASS

**Step 5: Update docs**

Document the normalized analytics contract in service/UI context docs.

**Step 6: Commit**

```bash
git add src/services/analytics_service.py src/services/data_service.py docs/context/services.qmd docs/context/ui.qmd tests/test_analytics_service.py tests/test_analytics_service_db.py
git commit -m "refactor: normalize analytics service inputs"
```

### Task 9: End-to-End Verification and Context Refresh

**Files:**
- Modify: `docs/project-index.qmd`
- Modify: `docs/context/importers.qmd`
- Modify: `docs/context/services.qmd`
- Modify: `docs/context/db.qmd`
- Modify: `docs/context/ui.qmd`
- Modify: `docs/context/testing.qmd`
- Test: `tests/`

**Step 1: Run the focused fast suite**

Run: `python -m pytest -m "not slow" -q`
Expected: PASS

**Step 2: Run the full suite if time permits**

Run: `python -m pytest -q`
Expected: PASS or only known slow/test-environment constraints.

**Step 3: Update all affected context docs**

Ensure every changed architectural boundary is reflected in the matching QMD file.

**Step 4: Sanity-check stale references**

Run: `rg -n "550 tests|554 tests|planned|pendiente|future work" docs/context docs/project-index.qmd docs/plan_mejoras.md`
Expected: no misleading architecture statements remain.

**Step 5: Commit**

```bash
git add docs/project-index.qmd docs/context/importers.qmd docs/context/services.qmd docs/context/db.qmd docs/context/ui.qmd docs/context/testing.qmd
git commit -m "docs: align context after architecture cleanup"
```
