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

# Enforce 85% minimum (CI requirement)
python -m pytest tests/ --cov=src --cov-fail-under=85

# Specific test class or function
python -m pytest tests/test_analytics_service.py::TestIsCategorized -v
```

Current test files (227 tests total):
- `tests/test_analytics_service.py` — analytics calculations
- `tests/test_data_service.py` — CSV loading
- `tests/test_validation.py` — transaction/tag validation
- `tests/test_rule_service.py` — rule staging/merging
- `tests/test_import_service.py` — import workflow
- `tests/test_common_utils.py` — utilities
- `tests/test_generic_importer.py` — import determinism
- `tests/test_healthcheck.py` — dependencies
- `tests/test_ui_pages_imports.py` — UI module imports

If tests fail, check `docs/context/testing.qmd` for debugging patterns.
