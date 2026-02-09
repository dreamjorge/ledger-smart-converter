---
name: ledger-smart-converter
description: Use this skill when working on the Ledger Smart Converter codebase for importer changes, categorization/rules updates, analytics/service changes, and test+coverage tasks. It provides the project-specific workflow using QMD context files, CodeGraph navigation, and the required 85% coverage gate.
---

# Ledger Smart Converter Skill

## When to use

Use this skill for any task in this repository involving:
- Bank importers (`src/import_*`, `src/generic_importer.py`, OCR/PDF flows)
- Rules/categorization (`config/rules*.yml`, `src/ml_categorizer.py`, `src/services/rule_service.py`)
- Services and analytics (`src/services/*`, `src/ui/pages/*`)
- Tests and coverage (`tests/*`, `pytest --cov=src --cov-fail-under=85`)

## Core workflow

1. Read only the relevant QMD context first:
- `docs/context/importers.qmd`
- `docs/context/services.qmd`
- `docs/context/ml-categorization.qmd`
- `docs/context/testing.qmd`
- `docs/context/ui.qmd`
- `docs/context/domain.qmd`
- `docs/project-index.qmd` (only when task spans multiple areas)

2. Use CodeGraph before broad file scanning:
- `codegraph_search "<symbol_or_module>"`
- `codegraph_callers "<function>"`
- `codegraph_callees "<function>"`
- `codegraph_impact "<symbol>"`
- If stale: `codegraph init -i`

3. Follow project-safe change rules:
- Do not edit `config/rules.yml` directly for manual rule additions; use pending workflow (`config/rules.pending.yml` + apply flow).
- Keep domain validation boundaries intact (`src/domain/transaction.py`, `src/validation.py`).
- Use structured logging, not `print()`.
- Avoid hardcoded paths; use `src/settings.py`.

4. TDD and verification are mandatory:
- Add/adjust tests first for new behavior or bug fixes.
- Run targeted tests, then full suite:
  - `python -m pytest tests/ -q`
  - `python -m pytest tests/ --cov=src --cov-fail-under=85`

## Task routing quick map

- Import/OCR issues: `docs/context/importers.qmd`, `src/pdf_utils.py`, `src/pdf_feedback.py`
- Rules/ML: `docs/context/ml-categorization.qmd`, `src/ml_categorizer.py`, `src/services/rule_service.py`
- UI features: `docs/context/ui.qmd`, `src/ui/pages/analytics_page.py`, `src/ui/pages/import_page.py`
- Analytics/data: `docs/context/services.qmd`, `src/services/analytics_service.py`, `src/services/data_service.py`
- Validation/domain: `docs/context/domain.qmd`, `src/domain/transaction.py`, `src/validation.py`

## Definition of done

- Behavior implemented with tests
- Relevant tests pass
- Coverage gate passes at `>=85%`
- No unsafe config/rules shortcuts
- Changes align with layer boundaries (domain/services/ui)
