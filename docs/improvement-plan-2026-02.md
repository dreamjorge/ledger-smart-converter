# Ledger Smart Converter - Improvement Plan (February 2026)

**Generated**: 2026-02-08
**Analysis Base**: Comprehensive codebase audit via Claude Code Explore agent
**CodeGraph Status**: ✅ Initialized (`.codegraph/codegraph.db`)
**Test Coverage**: 244 tests passing, critical gaps identified

---

## Executive Summary

The Ledger Smart Converter demonstrates **excellent architectural foundations** with a clean layered design, comprehensive service layer, and thoughtful patterns. However, **critical testing gaps exist in the most fragile components** (PDF/OCR processing and bank importers), creating operational risk.

**Overall Health Score**: 7.4/10
**Target Score After Phase 1**: 8.5/10

---

## 📊 Current State Snapshot

### Strengths ✅
- **Architecture**: Clean domain/services/UI separation, no circular dependencies
- **Testing Infrastructure**: 244 tests across 14 test files, good parametrization
- **Documentation**: Excellent project docs, QMD context system, comprehensive CLAUDE.md
- **Safety Mechanisms**: Atomic writes, validation layer, safe rules workflow
- **CI/CD**: GitHub Actions pipeline with pytest execution
- **Code Quality**: Minimal technical debt, typed errors, structured logging

### Critical Gaps 🔴
- **Untested Critical Paths**: PDF/OCR (507 lines), HSBC importer (601 lines), Santander importer (283 lines)
- **ML Module Untested**: ML categorizer (105 lines) has zero tests
- **Code Duplication**: 4 helper functions duplicated in analytics UI
- **Date Parsing Scattered**: 3 implementations across codebase
- **Debug Artifacts**: 20+ `print()` statements should use logger

---

## 🎯 Phase 1: Critical Testing & Cleanup (2 weeks)

**Goal**: Eliminate untested critical paths and architectural duplication
**Priority**: ⭐⭐⭐⭐⭐ BLOCKING FOR PRODUCTION

### Week 1: Critical Path Testing

#### 1.1 Add Tests for PDF/OCR Module (3-4 days)
**Files**: `src/pdf_utils.py` → `tests/test_pdf_utils.py`

**Context**: Read `docs/context/importers.qmd` (PDF utilities section)

**CodeGraph Navigation**:
```bash
# Find all functions in pdf_utils
codegraph_search "pdf_utils"

# Check what calls pdf extraction functions
codegraph_callers "extract_transactions_from_pdf"
```

**Test Requirements** (minimum 20 tests):
- `test_preprocess_for_ocr()` - Image preprocessing edge cases
- `test_ocr_image()` - Tesseract wrapper with mocked OCR
- `test_render_page()` - PDF page rendering (happy/error paths)
- `test_parse_mx_date()` - 15+ date format variants
- `test_extract_transactions_from_pdf()` - End-to-end extraction
- `test_collect_pdf_lines()` - Line collection with malformed PDFs
- `test_extract_pdf_metadata()` - Metadata extraction edge cases
- `test_amount_parsing()` - Currency parsing with edge cases

**Test Data Setup**:
```python
# Create fixtures in tests/fixtures/pdf_samples/
tests/
  fixtures/
    pdf_samples/
      valid_statement.pdf
      scanned_statement.pdf
      malformed_statement.pdf
      metadata_only.pdf
```

**Success Criteria**:
- [ ] 20+ tests covering all public functions
- [ ] Edge cases tested (None, empty, malformed)
- [ ] Error paths validated
- [ ] Coverage >85% for pdf_utils.py

#### 1.2 Add Tests for HSBC Importer (2-3 days)
**Files**: `src/import_hsbc_cfdi_firefly.py` → `tests/test_import_hsbc_cfdi_firefly.py`

**Context**: Read `docs/context/importers.qmd` (HSBC section)

**CodeGraph Navigation**:
```bash
# Find HSBC importer entry points
codegraph_search "import_hsbc"

# Check importer dependencies
codegraph_callees "process_hsbc_cfdi"
```

**Test Requirements** (minimum 25 tests):
- `test_parse_xml_structure()` - Valid/invalid XML
- `test_extract_rfc()` - RFC extraction from XML nodes
- `test_parse_transaction_amounts()` - Amount parsing edge cases
- `test_date_extraction()` - Date parsing variants
- `test_pdf_xml_reconciliation()` - PDF vs XML matching
- `test_statement_period_calculation()` - Period tagging logic
- `test_merchant_name_extraction()` - Merchant parsing
- `test_error_handling()` - Malformed input handling

**Test Data Setup**:
```python
tests/
  fixtures/
    hsbc/
      valid_statement.xml
      valid_statement.pdf
      malformed_cfdi.xml
      mismatched_pdf_xml/
```

**Success Criteria**:
- [ ] 25+ tests covering all parsing functions
- [ ] XML schema variations tested
- [ ] PDF-XML reconciliation validated
- [ ] Coverage >85% for import_hsbc_cfdi_firefly.py

#### 1.3 Add Tests for Santander Importer (2-3 days)
**Files**: `src/import_likeu_firefly.py` → `tests/test_import_likeu_firefly.py`

**Context**: Read `docs/context/importers.qmd` (Santander section)

**CodeGraph Navigation**:
```bash
# Find Santander importer functions
codegraph_search "import_likeu"

# Check data flow
codegraph_callees "process_likeu_excel"
```

**Test Requirements** (minimum 20 tests):
- `test_excel_header_detection()` - Header row identification
- `test_parse_es_date()` - Spanish date format parsing
- `test_amount_parsing()` - Currency parsing with decimals
- `test_merchant_extraction()` - Merchant name cleaning
- `test_statement_period_logic()` - Period calculation
- `test_pdf_verification()` - PDF metadata extraction
- `test_error_handling()` - Malformed Excel handling

**Test Data Setup**:
```python
tests/
  fixtures/
    santander/
      valid_statement.xlsx
      valid_statement.pdf
      malformed_excel.xlsx
      missing_columns.xlsx
```

**Success Criteria**:
- [ ] 20+ tests covering all parsing functions
- [ ] Excel format variations tested
- [ ] Date parsing edge cases validated
- [ ] Coverage >85% for import_likeu_firefly.py

### Week 2: Code Quality & Architecture Cleanup

#### 2.1 Remove Duplicate Functions in Analytics UI (2-4 hours)
**Files**: `src/ui/pages/analytics_page.py`

**Context**: Read `docs/context/ui.qmd` (Analytics section)

**Issue**: Functions defined twice (lines 229-356 and 481-609)

**CodeGraph Analysis**:
```bash
# Find duplicate function definitions
codegraph_search "_render_metrics"
codegraph_search "_render_charts"
codegraph_search "_render_category_deep_dive"
```

**Duplicates to Consolidate**:
1. `_render_metrics()` - lines 229-241 and 481-493
2. `_render_charts()` - lines 242-284 and 494-536
3. `_render_category_deep_dive()` - lines 285-326 and 537-578
4. `_render_monthly_spending_trends()` - lines 327-356 and 609+

**Refactoring Plan**:
```python
# Extract to helper module
src/ui/components/analytics_components.py

def render_metrics(df, bank_filter):
    """Render metrics cards with total spent and transaction count."""
    ...

def render_charts(df, metric_type):
    """Render distribution charts (category or bank)."""
    ...

def render_category_deep_dive(df, categories):
    """Render category breakdown with drill-down."""
    ...

def render_monthly_trends(df, periods):
    """Render monthly spending trend chart."""
    ...
```

**Success Criteria**:
- [ ] 4 helper functions consolidated into single module
- [ ] Both dashboard sections use shared components
- [ ] No behavioral changes (verified by existing tests)
- [ ] Reduced LOC by ~150 lines

#### 2.2 Consolidate Date Parsing Logic (3-4 hours)
**Files**: Create `src/date_utils.py`, update 3 importers

**Context**: Read `docs/context/importers.qmd` (Date parsing section)

**Issue**: Date parsing duplicated in 3 locations:
- `src/generic_importer.py:53-69` - `parse_es_date()`
- `src/import_likeu_firefly.py:38-57` - `parse_es_date()`
- `src/pdf_utils.py:168-254` - `parse_mx_date()`

**CodeGraph Analysis**:
```bash
# Find all date parsing calls
codegraph_search "parse_.*_date"
codegraph_callers "parse_es_date"
codegraph_callers "parse_mx_date"
```

**Refactoring Plan**:
```python
# Create new module: src/date_utils.py
from datetime import datetime
from typing import Optional

def parse_spanish_date(date_str: str) -> Optional[datetime]:
    """Parse Spanish date formats (dd/mm/yyyy, dd-mm-yyyy, etc.)."""
    ...

def parse_mexican_date(date_str: str) -> Optional[datetime]:
    """Parse Mexican bank date formats with month names."""
    ...

def parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 date formats (yyyy-mm-dd)."""
    ...
```

**Migration Steps**:
1. Create `src/date_utils.py` with consolidated functions
2. Write `tests/test_date_utils.py` (15+ tests for all formats)
3. Update `generic_importer.py` to import from date_utils
4. Update `import_likeu_firefly.py` to import from date_utils
5. Update `pdf_utils.py` to import from date_utils
6. Remove duplicate implementations
7. Run full test suite to verify

**Success Criteria**:
- [ ] Single source of truth for date parsing
- [ ] 15+ tests covering all date formats
- [ ] All importers use shared functions
- [ ] No behavioral regressions

#### 2.3 Replace print() with Logger (2-3 hours)
**Files**: `src/import_hsbc_cfdi_firefly.py`, `src/import_likeu_firefly.py`, `src/ml_categorizer.py`

**Context**: Read `docs/context/services.qmd` (Logging section)

**Issue**: 20+ `print()` statements should use structured logging

**CodeGraph Search**:
```bash
# Find all print statements in source
grep -r "print(" src/*.py | grep -v "# print" | wc -l
```

**Locations to Fix**:
- `src/import_hsbc_cfdi_firefly.py:291,348` - 2 debug prints
- `src/import_likeu_firefly.py:168,175` - 2 debug prints
- `src/ml_categorizer.py:40` - Training progress print
- `src/merge_suggestions.py` - Multiple status prints
- `src/pdf_feedback.py` - Multiple output prints (OK for CLI tool)

**Refactoring Pattern**:
```python
# Before
print(f"Processing {len(transactions)} transactions")

# After
from logging_config import get_logger
logger = get_logger(__name__)
logger.info("Processing transactions", extra={"count": len(transactions)})
```

**Success Criteria**:
- [ ] All `print()` in importers replaced with logger
- [ ] ML training uses logger.info() for progress
- [ ] Structured logging with context (extra={})
- [ ] CLI tools (pdf_feedback.py) can keep prints

---

## 🎯 Phase 2: ML Testing & Intermediate Priorities (2-3 weeks)

**Goal**: Test ML pipeline, improve observability, add coverage reporting
**Priority**: ⭐⭐⭐⭐ HIGH

### 2.1 Add Tests for ML Categorizer (2-3 days)
**Files**: `src/ml_categorizer.py` → `tests/test_ml_categorizer.py`

**Context**: Read `docs/context/ml-categorization.qmd`

**CodeGraph Navigation**:
```bash
# Analyze ML module structure
codegraph_search "TransactionCategorizer"
codegraph_callees "train_global_model"
codegraph_callees "predict_category"
```

**Test Requirements** (minimum 25 tests):
- `test_model_initialization()` - Constructor behavior
- `test_train_global_model()` - Model training with fixtures
- `test_predict_category()` - Prediction accuracy
- `test_save_model()` - Model persistence
- `test_load_model()` - Model loading (happy/error paths)
- `test_feature_extraction()` - Text feature engineering
- `test_confidence_scoring()` - Prediction confidence thresholds
- `test_model_retraining()` - Incremental training
- `test_empty_training_data()` - Edge case handling
- `test_malformed_model_file()` - Corruption handling

**Test Data Setup**:
```python
tests/
  fixtures/
    ml_models/
      valid_model.pkl
      corrupted_model.pkl
    training_data/
      categorized_transactions.csv
```

**Success Criteria**:
- [ ] 25+ tests covering all public methods
- [ ] Model training/loading validated
- [ ] Prediction accuracy thresholds tested
- [ ] Coverage >85% for ml_categorizer.py

### 2.2 Add Tests for Rule Merging (2 days)
**Files**: `src/merge_suggestions.py` → `tests/test_merge_suggestions.py`

**Context**: Read `docs/context/ml-categorization.qmd` (Rules section)

**CodeGraph Navigation**:
```bash
# Analyze rule merge logic
codegraph_search "merge_suggestions"
codegraph_callees "merge_rules"
```

**Test Requirements** (minimum 15 tests):
- `test_merge_no_conflicts()` - Clean merge
- `test_merge_with_conflicts()` - Conflict detection
- `test_priority_resolution()` - Rule priority handling
- `test_backup_creation()` - Backup workflow
- `test_yaml_parsing()` - YAML validation
- `test_regex_validation()` - Rule regex validation

**Success Criteria**:
- [ ] 15+ tests covering merge scenarios
- [ ] Conflict detection validated
- [ ] Coverage >80% for merge_suggestions.py

### 2.3 Enhance Generic Importer Tests (2 days)
**Files**: `tests/test_generic_importer.py`

**Context**: Read `docs/context/importers.qmd` (Generic importer section)

**Current State**: Partial indirect coverage via integration tests

**CodeGraph Analysis**:
```bash
# Check importer entry points
codegraph_search "generic_importer"
codegraph_impact "main"
```

**Additional Tests Needed**:
- CLI argument parsing
- Bank selection logic
- Error handling for unknown banks
- Dry-run mode validation
- Strict mode enforcement
- Log JSON output format

**Success Criteria**:
- [ ] 20+ tests (up from current coverage)
- [ ] All CLI flags tested
- [ ] Coverage >85% for generic_importer.py

### 2.4 Add Coverage Reporting to CI (4 hours)
**Files**: `.github/workflows/ci.yml`, `pyproject.toml` or `setup.cfg`

**Context**: Read `docs/context/testing.qmd` (CI section)

**Current CI Pipeline**:
```yaml
# .github/workflows/ci.yml (current)
- name: Run tests
  run: python -m pytest tests/ -v
```

**Enhanced CI Pipeline**:
```yaml
# Install pytest-cov
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install pytest-cov

# Run tests with coverage
- name: Run tests with coverage
  run: |
    python -m pytest tests/ -v \
      --cov=src \
      --cov-report=term \
      --cov-report=html \
      --cov-report=xml \
      --cov-fail-under=85

# Upload coverage to GitHub
- name: Upload coverage reports
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

**Configuration File** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --strict-markers"

[tool.coverage.run]
source = ["src"]
omit = [
    "src/web_app.py",  # Streamlit UI - difficult to test
    "src/ui/pages/*",  # UI pages - smoke tests only
    "src/translations.py",  # Static data
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
fail_under = 85
```

**Success Criteria**:
- [ ] Coverage reporting in CI pipeline
- [ ] Coverage badge in README
- [ ] 85% minimum coverage enforced
- [ ] HTML coverage reports generated

### 2.5 Create Database Schema Documentation (3 hours)
**Files**: `docs/database-schema.md`

**Context**: Read `docs/plan_mejoras.md` (Phase 2 - SQLite section)

**Content Structure**:
```markdown
# Database Schema (Planned)

## Overview
SQLite-based persistence layer for transaction history, rules, and imports.

## Tables

### transactions
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| date | DATE | NOT NULL | Transaction date |
| amount | DECIMAL(10,2) | NOT NULL | Amount in currency |
| ... | ... | ... | ... |

### accounts
...

### rules
...

### imports
...

## Indexes
...

## Migration Plan
...
```

**Success Criteria**:
- [ ] Complete schema documented
- [ ] Indexes and constraints defined
- [ ] Migration strategy outlined
- [ ] Deduplication logic explained

---

## 🎯 Phase 3: Polish & Optimization (Ongoing)

**Goal**: Documentation, performance, deployment readiness
**Priority**: ⭐⭐⭐ MEDIUM

### 3.1 Add Docstrings to Untested Modules (1 week)
**Files**: `src/pdf_utils.py`, `src/import_*.py`

**CodeGraph Usage**:
```bash
# Find functions lacking docstrings
codegraph_search "pdf_utils" | grep -v "docstring"
```

**Docstring Template**:
```python
def extract_transactions_from_pdf(pdf_path: str, config: dict) -> List[Transaction]:
    """Extract transactions from PDF bank statement using OCR.

    Args:
        pdf_path: Absolute path to PDF file
        config: Bank-specific configuration with regex patterns

    Returns:
        List of Transaction objects extracted from PDF

    Raises:
        ParseError: If PDF cannot be read or parsed
        OCRError: If Tesseract is not available and OCR is required

    Example:
        >>> config = load_bank_config("hsbc")
        >>> transactions = extract_transactions_from_pdf("statement.pdf", config)
        >>> len(transactions)
        45

    Note:
        Requires Tesseract OCR for scanned PDFs. Falls back to text extraction
        for text-based PDFs.
    """
    ...
```

**Modules to Document**:
- `src/pdf_utils.py` - 12 functions needing docstrings
- `src/import_hsbc_cfdi_firefly.py` - 17 functions
- `src/import_likeu_firefly.py` - 8 functions
- `src/ml_categorizer.py` - 6 methods

**Success Criteria**:
- [ ] 100% of public functions have docstrings
- [ ] Docstrings follow Google style (Args/Returns/Raises)
- [ ] Examples provided for complex functions

### 3.2 Enhance .env.example Documentation (1 hour)
**Files**: `.env.example`

**Current State** (4 entries, minimal docs):
```bash
# .env.example (current)
TESSERACT_CMD=
DATA_DIR=
RULES_FILE=
TEST_MODE=
```

**Enhanced Version**:
```bash
# .env.example (enhanced)

# OCR Configuration
# Path to Tesseract OCR executable (optional, only needed for scanned PDFs)
# Windows default: C:\Program Files\Tesseract-OCR\tesseract.exe
# Linux default: /usr/bin/tesseract
# macOS (homebrew): /usr/local/bin/tesseract
TESSERACT_CMD=/usr/bin/tesseract

# Data Storage
# Root directory for bank statement data (input files and generated CSVs)
# Default: ./data
# Structure: data/{bank}/firefly_{bank}.csv, unknown_merchants.csv
DATA_DIR=/root/ledger-smart-converter/data

# Configuration Files
# Path to main rules configuration file
# Default: ./config/rules.yml
# WARNING: Do not edit directly, use rules.pending.yml staging workflow
RULES_FILE=/root/ledger-smart-converter/config/rules.yml

# Testing Mode
# Enable test mode (skips external dependencies like OCR, uses mock data)
# Values: true, false
# Default: false
TEST_MODE=false

# Logging
# Log level for application logging (DEBUG, INFO, WARNING, ERROR)
# Default: INFO
LOG_LEVEL=INFO

# Streamlit Configuration (optional)
# Port for web interface
# Default: 8501
STREAMLIT_PORT=8501
```

**Success Criteria**:
- [ ] Each variable documented with purpose
- [ ] Default values specified
- [ ] OS-specific paths provided
- [ ] Warning for critical settings (RULES_FILE)

### 3.3 Create Deployment Runbook (4-6 hours)
**Files**: `docs/deployment-runbook.md`

**Content Structure**:
```markdown
# Deployment Runbook

## Pre-Deployment Checklist
- [ ] Python 3.8+ installed
- [ ] Tesseract OCR installed (optional)
- [ ] Sufficient disk space (500MB+ for data)
- [ ] Port 8501 available (or custom)

## Installation Steps

### Linux (Ubuntu/Debian)
...

### Windows (PowerShell)
...

### macOS (Homebrew)
...

## Configuration

### Environment Variables
...

### Rules Configuration
...

## Production Setup

### Systemd Service (Linux)
...

### Supervisor (Linux)
...

### Windows Service
...

## Backup & Recovery

### Database Backups
...

### Configuration Backups
...

### Disaster Recovery
...

## Monitoring

### Healthcheck Endpoint
...

### Log Monitoring
...

### Alerting
...

## Troubleshooting

### OCR Not Working
...

### Import Failures
...

### ML Model Issues
...
```

**Success Criteria**:
- [ ] Complete installation guide for 3 OS
- [ ] Systemd service template included
- [ ] Backup/recovery procedures documented
- [ ] Troubleshooting guide with common issues

### 3.4 Performance Optimizations (3-5 days)

#### 3.4.1 Cache Compiled Regex Patterns
**Files**: `src/common_utils.py`

**CodeGraph Analysis**:
```bash
# Find regex compilation calls
codegraph_search "re.compile"
codegraph_callers "apply_rules"
```

**Current Issue**:
```python
# Regex compiled on every call
def apply_rules(text: str, rules: List[dict]) -> Optional[str]:
    for rule in rules:
        pattern = re.compile(rule['regex'])  # Compiled every time
        if pattern.search(text):
            return rule['category']
```

**Optimized Version**:
```python
from functools import lru_cache

@lru_cache(maxsize=256)
def compile_regex(pattern: str) -> re.Pattern:
    """Cache compiled regex patterns for performance."""
    return re.compile(pattern)

def apply_rules(text: str, rules: List[dict]) -> Optional[str]:
    for rule in rules:
        pattern = compile_regex(rule['regex'])  # Cached
        if pattern.search(text):
            return rule['category']
```

**Impact**: 10-20% speedup on rule matching for large datasets

#### 3.4.2 Cache ML Model in Streamlit Session
**Files**: `src/web_app.py`

**Current Issue**:
```python
# Model loaded on every function call
def get_ml_engine():
    engine = ml.TransactionCategorizer()
    if not engine.load_model():
        return None
    return engine
```

**Optimized Version**:
```python
@st.cache_resource
def get_ml_engine():
    """Cache ML model in Streamlit session state."""
    engine = ml.TransactionCategorizer()
    if not engine.load_model():
        return None
    return engine
```

**Impact**: Faster page loads in Streamlit UI

**Success Criteria**:
- [ ] Regex patterns cached with LRU cache
- [ ] ML model cached in Streamlit session
- [ ] No behavioral changes
- [ ] Performance improvement measured

---

## 🎯 Phase 4: Nice-to-Have (Future)

**Priority**: ⭐⭐ LOW

### 4.1 Docker Containerization (2-3 days)
**Files**: `Dockerfile`, `.dockerignore`, `docker-compose.yml`

**Benefits**:
- Simplified deployment
- Isolated dependencies
- Portable across environments

**Container Layers**:
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ /app/src/
COPY config/ /app/config/
WORKDIR /app

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD python src/healthcheck.py || exit 1

# Run Streamlit
CMD ["streamlit", "run", "src/web_app.py", "--server.address", "0.0.0.0"]
```

### 4.2 Sphinx API Documentation (1 day)
**Files**: `docs/conf.py`, `docs/api/*.rst`

**Setup**:
```bash
pip install sphinx sphinx-rtd-theme
cd docs
sphinx-quickstart
```

**Configuration**:
```python
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Google-style docstrings
    'sphinx.ext.viewcode',
]
```

**Generated Documentation**:
- API reference from docstrings
- Searchable function index
- Cross-referenced modules

### 4.3 Schema Validation for rules.yml (2-3 days)
**Files**: `src/config_validator.py`, `config/rules.schema.json`

**JSON Schema Example**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["defaults", "rules"],
  "properties": {
    "defaults": {
      "type": "object",
      "properties": {
        "accounts": {
          "type": "object"
        }
      }
    },
    "rules": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "any_regex", "set"],
        "properties": {
          "name": {"type": "string"},
          "any_regex": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    }
  }
}
```

**Validation Function**:
```python
import jsonschema
import yaml

def validate_rules_config(config_path: str) -> List[str]:
    """Validate rules.yml against schema."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    with open('config/rules.schema.json') as f:
        schema = json.load(f)

    try:
        jsonschema.validate(config, schema)
        return []
    except jsonschema.ValidationError as e:
        return [str(e)]
```

---

## 📈 Success Metrics

### Phase 1 Completion Targets
| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| **Test Coverage** | ~70% | 85%+ | pytest --cov |
| **Untested Critical Modules** | 7 | 0 | Coverage report |
| **Code Duplication** | 4 instances | 0 | Manual review |
| **Print Statements** | 20+ | <5 | grep "print(" |
| **Overall Health Score** | 7.4/10 | 8.5/10 | Scorecard |

### Phase 2 Completion Targets
| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| **CI Coverage Reporting** | None | Active | GitHub Actions |
| **ML Module Tests** | 0 | 25+ | pytest count |
| **Documentation Coverage** | 60% | 90%+ | Docstring audit |
| **Database Schema** | None | Documented | Schema file exists |

### Phase 3 Completion Targets
| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| **Deployment Automation** | Partial | Complete | Scripts exist |
| **Performance** | Baseline | +20% | Benchmark |
| **Runbook Completeness** | None | Complete | Runbook exists |

---

## 🛠️ CodeGraph-Assisted Workflow

### Using CodeGraph for Impact Analysis
Before making changes, analyze impact:

```bash
# Find what depends on a function before refactoring
codegraph_impact "parse_es_date"

# Check callers before changing signature
codegraph_callers "extract_transactions_from_pdf"

# Find all implementations of a pattern
codegraph_search "def parse.*date"
```

### Using QMD Context for Focused Work
Before starting a task, read relevant context:

```bash
# Working on importers
cat docs/context/importers.qmd

# Working on ML categorization
cat docs/context/ml-categorization.qmd

# Writing tests
cat docs/context/testing.qmd
```

### Integration with Slash Commands
Use project slash commands for common tasks:

```bash
# Run tests with coverage
/coverage

# Validate configuration
/validate-config

# Create new test file
/new-test pdf_utils

# Check system health
/health
```

---

## 📋 Prioritized Task Backlog

### Critical (Do First) 🔴
1. [ ] Add tests for `pdf_utils.py` (20+ tests)
2. [ ] Add tests for `import_hsbc_cfdi_firefly.py` (25+ tests)
3. [ ] Add tests for `import_likeu_firefly.py` (20+ tests)
4. [ ] Remove duplicate functions in analytics UI
5. [ ] Consolidate date parsing logic

### High (Do Next) 🟠
6. [ ] Add tests for `ml_categorizer.py` (25+ tests)
7. [ ] Add tests for `merge_suggestions.py` (15+ tests)
8. [ ] Enhance `generic_importer.py` tests (20+ tests)
9. [ ] Replace print() with logger (20+ locations)
10. [ ] Add coverage reporting to CI

### Medium (Nice to Have) 🟡
11. [ ] Create database schema documentation
12. [ ] Add docstrings to pdf_utils.py
13. [ ] Add docstrings to importers
14. [ ] Enhance .env.example documentation
15. [ ] Create deployment runbook
16. [ ] Cache regex patterns
17. [ ] Cache ML model in Streamlit

### Low (Future) 💚
18. [ ] Docker containerization
19. [ ] Sphinx API documentation
20. [ ] Schema validation for rules.yml
21. [ ] Performance profiling dashboard
22. [ ] GraphQL API layer

---

## 🎓 Implementation Guidelines

### Test-Driven Development (TDD)
For all new test creation:

1. **Red**: Write failing test first
2. **Green**: Implement minimal code to pass
3. **Refactor**: Clean up while keeping tests green

### Git Workflow
```bash
# Create feature branch
git checkout -b test/pdf-utils-coverage

# Write tests (commit as you go)
git add tests/test_pdf_utils.py
git commit -m "test: add initial pdf_utils tests (5 tests)"

# Verify tests fail (red phase)
pytest tests/test_pdf_utils.py

# Implement fixes/features
# ...

# Commit when tests pass (green phase)
git add src/pdf_utils.py
git commit -m "feat: improve pdf extraction error handling"

# Push and create PR
git push origin test/pdf-utils-coverage
```

### Code Review Checklist
- [ ] Tests written before code (TDD)
- [ ] Coverage ≥85% for new code
- [ ] Docstrings added for public functions
- [ ] No new print() statements (use logger)
- [ ] No code duplication
- [ ] Type hints present
- [ ] Error handling validated
- [ ] Integration tests pass

---

## 📞 Getting Help

- **Architecture Questions**: Read `docs/project-index.qmd`
- **Module-Specific Work**: Read `docs/context/<area>.qmd`
- **Testing Strategy**: Read `docs/context/testing.qmd`
- **Roadmap Context**: Read `docs/plan_mejoras.md`
- **CodeGraph Usage**: See `AGENTS.md` (CodeGraph section)

---

## 🎯 Next Actions (This Week)

1. **Create test fixtures** for PDF/OCR testing
2. **Start with pdf_utils tests** (highest impact, most critical)
3. **Set up coverage reporting** in CI (enables tracking)
4. **Review QMD context files** before starting each module
5. **Use CodeGraph** for impact analysis before refactoring

**Estimated Time to Phase 1 Completion**: 2 weeks with dedicated effort
**Estimated ROI**: High (eliminates critical risk in production paths)
