# Context Files for AI Agents

This directory contains modular QMD (Quarto Markdown) files that provide focused context for AI agents working on specific parts of the codebase.

## Purpose

Instead of loading the entire project context (which uses many tokens), agents can read only the relevant QMD file for their current task. This improves:

- 📉 **Token efficiency** - Load only what's needed
- 🎯 **Focused context** - No irrelevant information
- 📚 **Comprehensive examples** - Code patterns and best practices
- 🔄 **Maintainability** - Easy to update and keep current

## Available Context Files

### 1. Domain Layer (`domain.qmd`)

**Read this when working on:**
- Transaction models
- Data validation
- Canonical data structures
- Error types

**Key Topics:**
- CanonicalTransaction dataclass
- Validation rules
- Firefly III CSV format
- Hash-based deduplication
- Common modifications

**Files covered:** `src/domain/transaction.py`, `src/validation.py`, `src/errors.py`

---

### 2. Services Layer (`services.qmd`)

**Read this when working on:**
- Import workflow
- Rule management
- Analytics calculations
- Data access layer

**Key Topics:**
- Import service (CSV operations)
- Rule service (staging, merging, conflicts)
- Analytics service (dashboard stats)
- Data service (loading CSVs)
- Service patterns (DI, error handling, logging)

**Files covered:** `src/services/*.py`

---

### 3. Bank Importers (`importers.qmd`)

**Read this when working on:**
- Bank-specific parsers
- PDF extraction
- Adding new bank support
- OCR debugging

**Key Topics:**
- HSBC CFDI importer (XML/PDF)
- Santander LikeU importer (XLSX/PDF)
- Generic importer CLI
- PDF utilities (extraction, OCR, date/amount parsing)
- Adding new banks (step-by-step guide)

**Files covered:** `src/import_*_firefly.py`, `src/generic_importer.py`, `src/pdf_utils.py`

---

### 4. UI Layer (`ui.qmd`)

**Read this when working on:**
- Streamlit pages
- Analytics dashboard
- Rule correction UI
- User interactions

**Key Topics:**
- App router (`web_app.py`)
- Import page (file upload, processing)
- Analytics page (metrics, charts, drilldown)
- Filtering system (period, date range)
- Rule Hub (fuzzy search, ML predictions, staging)
- Translation system
- Plotly charts

**Files covered:** `src/ui/pages/*.py`, `src/web_app.py`, `src/translations.py`

---

### 5. ML & Categorization (`ml-categorization.qmd`)

**Read this when working on:**
- ML predictions
- Categorization rules
- Fuzzy merchant matching
- Category suggestions

**Key Topics:**
- ML model (sklearn Naive Bayes + TF-IDF)
- Training process and triggers
- Smart matching (fuzzy search with rapidfuzz)
- Rule-based categorization
- Safe rule workflow (staging, conflicts, merging)
- Merchant tagging
- Category hierarchy

**Files covered:** `src/ml_categorizer.py`, `src/smart_matching.py`, `src/services/rule_service.py`, `config/rules.yml`

---

### 6. Testing (`testing.qmd`)

**Read this when working on:**
- Writing tests
- Understanding test suite
- CI/CD pipeline
- Test patterns

**Key Topics:**
- Test structure (55 tests across 8 files)
- Key test suites (analytics, data service, validation)
- Running tests (pytest commands)
- Test patterns (fixtures, parametrization, mocking)
- CI/CD (GitHub Actions)
- Coverage areas
- Adding new tests

**Files covered:** `tests/*.py`, `.github/workflows/ci.yml`

---

## How to Use

### For AI Agents

**1. Identify your task area:**
```
Domain models → domain.qmd
Import logic → importers.qmd + services.qmd
Dashboard → ui.qmd + services.qmd
Categorization → ml-categorization.qmd
Testing → testing.qmd
```

**2. Load the relevant QMD file:**
```python
from pathlib import Path

context = Path("docs/context/domain.qmd").read_text()
# Now you have focused context for working on domain models
```

**3. Reference specific sections:**
QMD files are organized with clear markdown headers. Search for specific topics within the file.

**4. For comprehensive overview:**
If you need full project context, read `docs/project-index.qmd` instead.

### For Humans

**View as HTML (recommended):**

All QMD files have been rendered to HTML for easy viewing in a browser:

```bash
# Open in browser (Linux)
xdg-open docs/context/domain.html

# Open in browser (macOS)
open docs/context/domain.html

# Open in browser (Windows)
start docs/context/domain.html
```

**View as Markdown:**

QMD files are valid markdown and can be read in any text editor or markdown viewer:

```bash
cat docs/context/domain.qmd
```

**Re-render to HTML:**

If you edit a QMD file, re-render it with Quarto:

```bash
cd docs/context
quarto render domain.qmd
```

Or render all at once:

```bash
cd docs/context
for file in *.qmd; do quarto render "$file"; done
```

## File Sizes

QMD files are designed to be comprehensive yet concise:

| File | Size | Lines | Topics |
|------|------|-------|--------|
| `domain.qmd` | ~6KB | ~150 | Transaction model, validation |
| `services.qmd` | ~12KB | ~300 | 4 services, patterns, examples |
| `importers.qmd` | ~15KB | ~400 | 3 importers, PDF utils, new bank guide |
| `ui.qmd` | ~18KB | ~500 | Router, 2 pages, filters, charts |
| `ml-categorization.qmd` | ~14KB | ~350 | ML, fuzzy matching, rules |
| `testing.qmd` | ~12KB | ~300 | Test suite, patterns, CI/CD |

**Total:** ~77KB of focused context across 6 modules

Compare to reading entire codebase: ~500KB+

**Token savings:** ~85% when reading specific context vs. entire codebase

## Maintenance

**When to update QMD files:**

- ✅ After adding new features
- ✅ After architectural changes
- ✅ After significant refactoring
- ✅ When examples become outdated
- ✅ When file paths change

**Updating workflow:**

1. Edit the relevant QMD file
2. Re-render to HTML: `quarto render <file>.qmd`
3. Verify changes in browser
4. Commit both QMD and HTML files

## Integration with AGENTS.md

The main `AGENTS.md` file at the project root references these context files and provides a routing guide:

```markdown
## Working on Domain/Validation
- Read: `docs/context/domain.qmd`
- Files: `src/domain/transaction.py`, ...
```

This creates a two-tier documentation system:
- **Tier 1:** Quick reference in `AGENTS.md` (routing)
- **Tier 2:** Detailed context in `docs/context/*.qmd` (deep dives)

## Benefits Over Single Large File

**Before** (single AGENTS.md):
- ❌ Load entire context for small tasks
- ❌ Hard to navigate
- ❌ High token usage
- ❌ Difficult to maintain

**After** (modular QMD files):
- ✅ Load only what's needed
- ✅ Easy to find relevant info
- ✅ 85% token reduction
- ✅ Each file focused and maintainable
- ✅ Rendered HTML for humans
- ✅ Markdown for agents

## Quick Examples

### Example 1: Working on Analytics Dashboard

**Agent reads:**
```python
context = Path("docs/context/ui.qmd").read_text()
service_context = Path("docs/context/services.qmd").read_text()

# Now has full context for:
# - Analytics page structure
# - Chart rendering
# - Filtering system
# - Analytics service API
# - Stats calculation logic
```

**Token usage:** ~30KB (vs 500KB for entire codebase)

### Example 2: Adding New Bank Importer

**Agent reads:**
```python
context = Path("docs/context/importers.qmd").read_text()

# Contains:
# - Step-by-step guide for new banks
# - Code templates
# - Parser patterns
# - PDF utilities reference
# - Configuration schema
```

**Token usage:** ~15KB

### Example 3: Writing Tests

**Agent reads:**
```python
context = Path("docs/context/testing.qmd").read_text()

# Contains:
# - Test structure overview
# - Test patterns and examples
# - Fixture usage
# - Pytest commands
# - CI/CD info
```

**Token usage:** ~12KB

## Additional Resources

- **Full project overview:** `docs/project-index.qmd` (comprehensive reference)
- **Main agent guide:** `AGENTS.md` (quick reference + routing)
- **Recent changes:** `CHANGES.md` (change log)
- **Roadmap:** `docs/plan_mejoras.md` (future plans)

---

**Created:** 2026-02-06
**Format:** Quarto Markdown (QMD)
**Rendering:** Quarto 1.6.39
**Purpose:** Token-efficient AI agent context
