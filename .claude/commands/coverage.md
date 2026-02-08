# Run Tests with Coverage Enforcement

Run the full test suite enforcing 85% minimum coverage. $ARGUMENTS

## Coverage Commands

```bash
# Enforce 85% minimum (fails if below threshold)
python -m pytest tests/ --cov=src --cov-fail-under=85

# Full report with missing lines
python -m pytest tests/ --cov=src --cov-fail-under=85 --cov-report=term-missing

# HTML report (open htmlcov/index.html)
python -m pytest tests/ --cov=src --cov-fail-under=85 --cov-report=html

# Per-module breakdown
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-config=.coveragerc
```

## Coverage Targets

| Area | Minimum | Current |
|------|---------|---------|
| All new code | 85% | — |
| Critical paths (imports, validation, ML) | 90% | ~90% |
| Domain models | 85% | ~100% |
| Utilities | 85% | ~90% |

## If Coverage Drops Below 85%

1. Identify uncovered modules: look for red lines in `--cov-report=term-missing`
2. Write tests for uncovered paths (use `/new-test <module>`)
3. Focus on: error handling, edge cases, conditional branches
4. Re-run until coverage passes

See `docs/context/testing.qmd` for test writing patterns.
