# Run Tests

Run the project test suite. $ARGUMENTS

Execute the appropriate test command:

```bash
# All tests (verbose)
python -m pytest tests/ -v

# Quick run
python -m pytest tests/ -q

# Specific file
python -m pytest tests/<file>.py -v

# With coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Specific test class or function
python -m pytest tests/test_analytics_service.py::TestIsCategorized -v
```

Current test coverage areas:
- `tests/test_analytics_service.py` — 24 tests (analytics calculations)
- `tests/test_data_service.py` — 11 tests (CSV loading)
- `tests/test_validation.py` — 10 tests (transaction/tag validation)
- `tests/test_rule_service.py` — 2 tests (rule staging/merging)
- `tests/test_import_service.py` — 2 tests (import workflow)
- `tests/test_common_utils.py` — 2 tests (utilities)
- `tests/test_generic_importer.py` — 1 test (import determinism)
- `tests/test_healthcheck.py` — 1 test (dependencies)
- `tests/test_ui_pages_imports.py` — 1 test (UI module imports)

If tests fail, check `docs/context/testing.qmd` for debugging patterns.
