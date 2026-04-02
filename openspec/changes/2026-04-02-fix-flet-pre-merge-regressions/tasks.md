# Tasks: Fix Flet Pre-Merge Regressions

## Phase 1: Infrastructure and RED Tests

- [ ] 1.1 Bootstrap the repo if `.venv` is missing with `pwsh ./scripts/setup_env.ps1` or `bash ./scripts/setup_env.sh`, then verify the test runner with `.venv\Scripts\python.exe -V`.
- [ ] 1.2 Add failing regression tests in `tests/test_db_service.py` for account-aware `source_hash` generation and duplicate checks across same-account vs cross-account transactions.
- [ ] 1.3 Add failing regression tests in `tests/test_dedup_service.py` covering repeated rows inside a single batch before SQLite insert/resolve logic runs.
- [ ] 1.4 Add failing regression tests in `tests/test_data_service.py`, `tests/test_manual_entry_service.py`, and the relevant Flet Rule Hub test module for all-accounts analytics loading, canonical category loading, and retraining-on-merge behavior.

## Phase 2: Implementation

- [ ] 2.1 Update `src/services/db_service.py` so `build_source_hash()` and duplicate lookups include account context without breaking same-account dedup semantics.
- [ ] 2.2 Update `src/services/dedup_service.py` to detect duplicate hashes already repeated in the incoming batch and surface them through the existing resolution flow.
- [ ] 2.3 Fix the all-accounts analytics path in `src/services/data_service.py` and `src/ui/pages/analytics_page.py` so global loads never call a bank-scoped loader with `bank_id=None`.
- [ ] 2.4 Fix `src/services/manual_entry_service.py` to load categories from canonical rule data (`rules[*].set.expense`) instead of the legacy shape.
- [ ] 2.5 Update `src/services/rule_service.py` and `src/ui/flet_ui/rule_hub_view.py` so Flet merges retrain only after a successful merge and all Rule Hub category choices come from canonical categories.

## Phase 3: Verification and Documentation

- [ ] 3.1 Update `docs/context/db.qmd`, `docs/context/services.qmd`, `docs/context/ui.qmd`, and `docs/context/testing.qmd` with the new hash inputs, dedup flow, analytics loader path, and canonical category/retraining behavior.
- [ ] 3.2 Verify targeted regressions with `.venv\Scripts\python.exe -m pytest tests/test_db_service.py tests/test_dedup_service.py tests/test_data_service.py tests/test_manual_entry_service.py -q` plus the Flet Rule Hub test module added in 1.4.
- [ ] 3.3 Run a broader confidence pass with `.venv\Scripts\python.exe -m pytest -q -k "dedup or analytics or manual_entry or rule_hub or db_service"` and capture any follow-up fixes before merge.
