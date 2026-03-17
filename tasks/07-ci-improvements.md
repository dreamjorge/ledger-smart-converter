# Task: CI/CD Pipeline Improvements

**Priority**: High
**Effort**: Small (30 min)
**Files**: `.github/workflows/ci.yml`

---

## Why

The CI pipeline has three problems:

1. **Coverage threshold mismatch**: CI enforces 60% but `AGENTS.md` says 85% and
   `docs/context/testing.qmd` says 85%. This is a dangerous inconsistency — a PR can
   pass CI while violating the project's own policy.

2. **Full test suite in CI**: CI runs `pytest -q` (all tests including `@pytest.mark.slow`).
   ML training tests take 3+ min each — on a CI machine (cold sklearn import), the full
   suite can exceed 30 min or timeout. Using `-m "not slow"` keeps CI fast and focused.

3. **No DB schema compile check**: `src/database/schema.sql` is never syntax-validated
   in CI. A broken schema would only be caught at runtime.

---

## Change 1: Raise coverage threshold from 60% to 80%

The current 60% is a legacy placeholder. The actual codebase is at ~88%.
Moving to 80% is safe and closes the gap with the stated 85% policy.
(Keep it at 80% rather than 85% to allow headroom for new work in progress.)

```diff
-          --cov-fail-under=60 \
+          --cov-fail-under=80 \
```

---

## Change 2: Run only fast tests in CI; run slow tests separately

```yaml
    - name: Run fast tests with coverage
      run: |
        python -m pytest \
          -m "not slow" \
          --cov=src \
          --cov-report=term \
          --cov-report=html \
          --cov-config=.coveragerc \
          --cov-fail-under=80 \
          -q

    - name: Run slow ML tests (no coverage threshold)
      run: |
        python -m pytest \
          -m "slow" \
          -q \
          --tb=short
```

Splitting the steps lets CI fail fast on business logic regressions without waiting
for sklearn training to complete.

---

## Change 3: Add schema syntax validation

Add after the existing compile checks:

```yaml
    - name: Validate DB schema syntax
      run: |
        python -c "
        import sqlite3, pathlib
        sql = pathlib.Path('src/database/schema.sql').read_text()
        conn = sqlite3.connect(':memory:')
        conn.executescript(sql)
        conn.close()
        print('schema.sql: OK')
        "
```

This costs <1 second and catches broken SQL before any test runs.

---

## Change 4 (optional): Cache pip dependencies

```yaml
    - name: Cache pip
      uses: actions/cache@v4
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
```

Add before the "Install dependencies" step. Reduces CI time by ~60s on cache hit.

---

## Acceptance Criteria

- [ ] Coverage threshold in CI is ≥ 80%
- [ ] Fast tests (`-m "not slow"`) run as the primary step
- [ ] Slow ML tests run as a separate step
- [ ] Schema syntax validated before tests
- [ ] (Optional) pip caching in place
