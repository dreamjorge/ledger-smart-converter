# Phase 1 Continuation Plan

**Generated**: 2026-02-08
**Context**: Token usage optimization for multi-agent handoff
**Current Session**: Initial Phase 1 execution

---

## 📊 Progress So Far (Session 1)

### ✅ Completed Tasks
1. **Task #1**: Add unit tests for pdf_utils.py module (62 tests)
   - File: `tests/test_pdf_utils.py`
   - Coverage: All 9 public functions tested
   - Status: ✅ Complete - 62 tests passing

5. **Task #5**: Consolidate date parsing to date_utils.py (48 tests)
   - Files created:
     - `src/date_utils.py` - Unified date parsing module
     - `tests/test_date_utils.py` - 48 comprehensive tests
   - Files updated:
     - `src/generic_importer.py` - Uses `parse_spanish_date` from date_utils
     - `src/import_likeu_firefly.py` - Uses `parse_spanish_date` from date_utils
     - `src/pdf_utils.py` - Imports `parse_mexican_date` from date_utils
   - Status: ✅ Complete - 48 tests passing

### 📈 Test Suite Growth
- **Before**: 244 tests
- **After**: 354 tests (+110 tests)
- **All Passing**: ✅

---

## 🎯 Remaining Phase 1 Tasks

### High Priority (Week 1)

#### Task #2: Add unit tests for HSBC importer
**File**: `src/import_hsbc_cfdi_firefly.py` (601 lines, 0 tests)
**Create**: `tests/test_import_hsbc_cfdi_firefly.py`

**Required Tests** (minimum 25):
- XML parsing (`parse_xml_structure`, `extract_rfc`)
- Transaction parsing (`parse_transaction_amounts`, `date_extraction`)
- PDF-XML reconciliation (`reconcile_pdf_xml`)
- Statement period calculation
- Merchant name extraction
- Error handling (malformed XML, missing fields)

**Test Fixtures Needed**:
```
tests/fixtures/hsbc/
  valid_statement.xml
  valid_statement.pdf
  malformed_cfdi.xml
  missing_fields.xml
```

**CodeGraph Commands**:
```bash
codegraph_search "import_hsbc"
codegraph_callees "process_hsbc_cfdi"
codegraph_callers "extract_transactions_from_xml"
```

**Context**: Read `docs/context/importers.qmd` (HSBC section)

#### Task #3: Add unit tests for Santander importer
**File**: `src/import_likeu_firefly.py` (283 lines, 0 tests)
**Create**: `tests/test_import_likeu_firefly.py`

**Required Tests** (minimum 20):
- Excel header detection (`find_header_row`)
- Date parsing (Spanish format) - Now uses `date_utils.parse_spanish_date`
- Amount parsing with decimals
- Merchant extraction and cleaning
- Statement period logic
- PDF metadata verification
- Error handling (malformed Excel, missing columns)

**Test Fixtures Needed**:
```
tests/fixtures/santander/
  valid_statement.xlsx
  valid_statement.pdf
  malformed_excel.xlsx
  missing_columns.xlsx
```

**CodeGraph Commands**:
```bash
codegraph_search "import_likeu"
codegraph_callees "process_likeu_excel"
codegraph_callers "find_header_row"
```

**Context**: Read `docs/context/importers.qmd` (Santander section)

### Medium Priority (Week 2)

#### Task #4: Remove duplicate functions in analytics UI
**File**: `src/ui/pages/analytics_page.py`

**Duplicates** (lines 229-356 and 481-609):
- `_render_metrics()` - 2 instances
- `_render_charts()` - 2 instances
- `_render_category_deep_dive()` - 2 instances
- `_render_monthly_spending_trends()` - 2 instances

**Refactor To**: `src/ui/components/analytics_components.py`

**Steps**:
1. Create `src/ui/components/` directory
2. Create `analytics_components.py` with 4 shared functions
3. Update `analytics_page.py` to import from components
4. Delete duplicate definitions
5. Run tests to verify no behavioral changes

**Expected LOC Reduction**: ~150 lines

#### Task #6: Replace print() with structured logging
**Files**:
- `src/import_hsbc_cfdi_firefly.py:291,348` (2 instances)
- `src/import_likeu_firefly.py:168,175` (2 instances)
- `src/ml_categorizer.py:40` (1 instance)
- `src/merge_suggestions.py` (multiple instances)

**Pattern**:
```python
# Before
print(f"Processing {count} transactions")

# After
from logging_config import get_logger
logger = get_logger(__name__)
logger.info("Processing transactions", extra={"count": count})
```

**Grep Commands**:
```bash
# Find all print statements in source
grep -n "print(" src/*.py | grep -v "# print"

# Check after replacement
grep -n "print(" src/*.py
```

#### Task #7: Add coverage reporting to CI pipeline
**Files**: `.github/workflows/ci.yml`, `pyproject.toml`

**Steps**:
1. Install pytest-cov in requirements: `pip install pytest-cov`
2. Create `pyproject.toml` with coverage configuration
3. Update `.github/workflows/ci.yml` to run with coverage
4. Add coverage badge to README.md
5. Set minimum threshold: 85%

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers"

[tool.coverage.run]
source = ["src"]
omit = ["src/web_app.py", "src/ui/pages/*", "src/translations.py"]

[tool.coverage.report]
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

---

## 🔄 Agent Handoff Instructions

When this session approaches 98% token usage (196,000 / 200,000 tokens), follow these steps:

### 1. Save Current State
Create a checkpoint file with current progress:

```bash
# Create checkpoint
cat > docs/phase1-checkpoint-$(date +%Y%m%d).md <<EOF
# Phase 1 Checkpoint - $(date +%Y-%m-%d)

## Completed This Session
- Task #1: pdf_utils tests (62 tests) ✅
- Task #5: date_utils consolidation (48 tests) ✅

## Next Task to Start
- Task #2: HSBC importer tests (25+ tests)

## Test Count
- Current: 354 tests passing
- Target for Phase 1: 450+ tests

## Files Modified
- Created: src/date_utils.py, tests/test_date_utils.py, tests/test_pdf_utils.py
- Modified: src/generic_importer.py, src/import_likeu_firefly.py, src/pdf_utils.py

## No Merge Conflicts Expected
All changes are additive (new files) or isolated (import statements).
EOF
```

### 2. Update Task Status
```bash
# Mark current task status
# Task #1: completed
# Task #5: completed
# Task #2: pending (ready to start)
```

### 3. Commit Progress
```bash
git add -A
git commit -m "feat: phase 1 progress - pdf_utils tests + date consolidation (110 new tests)

- Add comprehensive pdf_utils.py test suite (62 tests)
- Consolidate date parsing to date_utils.py (48 tests)
- Update importers to use unified date parsing
- Test count: 244 → 354 (+110 tests)

Related: Phase 1 improvement plan, Tasks #1 and #5

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### 4. Instructions for Next Agent

Add to `docs/phase1-continuation-plan.md`:

```markdown
## 🤖 For Next Agent (Session 2)

### Quick Start
1. Read this file: `docs/phase1-continuation-plan.md`
2. Read roadmap: `docs/improvement-plan-2026-02.md`
3. Check test count: `python -m pytest tests/ -q` (should be 354+)
4. Review task list: Use Task tool or check `docs/phase1-continuation-plan.md`

### Next Task: HSBC Importer Tests
**Priority**: High (Critical path untested)
**File**: `src/import_hsbc_cfdi_firefly.py`

**Steps**:
1. Read context: `cat docs/context/importers.qmd | grep -A 100 "HSBC"`
2. Analyze module: `codegraph_search "import_hsbc"`
3. Create fixtures: `mkdir -p tests/fixtures/hsbc/`
4. Create test file: `tests/test_import_hsbc_cfdi_firefly.py`
5. Write 25+ tests covering XML parsing, PDF reconciliation, error handling
6. Run tests: `pytest tests/test_import_hsbc_cfdi_firefly.py -v`
7. Verify coverage: `pytest tests/test_import_hsbc_cfdi_firefly.py --cov=src/import_hsbc_cfdi_firefly`
8. Mark task complete: Update task #2 status

**Expected Outcome**:
- 25+ new tests for HSBC importer
- Test count: 354 → 379+
- Coverage >85% for import_hsbc_cfdi_firefly.py

### After HSBC Tests
Continue with Task #3 (Santander importer tests), following same pattern.

### Communication
If you complete more tasks, update this file with your progress and create a new checkpoint.
```

---

## 📚 Reference Files for Next Agent

### Essential Reading (in order)
1. `docs/phase1-continuation-plan.md` (this file)
2. `docs/improvement-plan-2026-02.md` (full Phase 1 plan)
3. `docs/context/importers.qmd` (importer architecture)
4. `AGENTS.md` (agent guidelines)

### Key Commands
```bash
# Check current test count
python -m pytest tests/ -q

# View task list
cat docs/phase1-continuation-plan.md | grep "Task #"

# Run specific test file
pytest tests/test_import_hsbc_cfdi_firefly.py -v

# Check what's been done
git log --oneline -10
```

### CodeGraph Usage
```bash
# Explore HSBC importer
codegraph_search "hsbc"
codegraph_callees "process_hsbc_cfdi"
codegraph_impact "extract_transactions_from_xml"

# Explore Santander importer
codegraph_search "likeu"
codegraph_callees "process_likeu_excel"
```

---

## 🎯 Success Criteria for Phase 1 Completion

- [ ] Task #1: pdf_utils tests (62 tests) ✅
- [ ] Task #2: HSBC importer tests (25+ tests)
- [ ] Task #3: Santander importer tests (20+ tests)
- [ ] Task #4: Remove UI duplicates (~150 LOC reduction)
- [ ] Task #5: Date parsing consolidation ✅
- [ ] Task #6: Replace print() with logger
- [ ] Task #7: Add coverage reporting to CI

**Total Test Count Target**: 450+ tests (current: 354)
**Coverage Target**: 85%+ across all modules
**Estimated Time**: 1-2 weeks

---

## 💡 Tips for Continuity

1. **Always run tests first**: `pytest tests/ -q` to verify baseline
2. **Read context before coding**: Use QMD files for module-specific knowledge
3. **Use CodeGraph for analysis**: Faster than grepping through files
4. **Commit frequently**: Small, atomic commits with clear messages
5. **Update this file**: Add your progress so the next agent knows what's done
6. **Follow TDD**: Write tests first, then implement fixes

---

## 🔗 Related Documentation

- Full plan: `docs/improvement-plan-2026-02.md`
- Architecture: `docs/context/*.qmd`
- Agent guide: `AGENTS.md`
- Roadmap: `docs/plan_mejoras.md`
- Test guide: `docs/context/testing.qmd`
