# Ledger Smart Converter - Big Picture and Development Roadmap

**Last Updated**: 2026-02-13  
**Audience**: Humans and AI agents working in this repository

## 1) What This Project Is

Ledger Smart Converter ingests raw bank statement files (XLSX, XML, PDF/OCR), normalizes and categorizes transactions, and exports Firefly III compatible CSV while powering an analytics dashboard.

Core objective:
- Reliable personal-finance transaction processing with auditable transformations.

Secondary objectives:
- High automatic categorization coverage.
- Idempotent re-processing.
- Fast iteration for adding new banks/rules.

## 2) Architecture at a Glance

Layers:
- Domain: canonical transaction contracts and validation.
- Importers: bank-specific parsing.
- Services: orchestration (migration, rules, analytics, export).
- UI: Streamlit pages for import + analytics + rule correction.
- Persistence: SQLite (`data/ledger.db`) plus compatibility CSV exports.

Primary path:
1. Input files parsed by importer.
2. Canonical transaction generated.
3. Description normalization applied (`raw_description` + `normalized_description`).
4. Categorization (rules first, ML fallback).
5. Stored in DB with dedup hash.
6. Exported as Firefly CSV and consumed by analytics.

## 3) Current State (Reality Check)

Implemented:
- Canonical account mapping and validation pipeline.
- DB schema, migrator, one-command DB pipeline, Firefly exporter.
- Deterministic description normalizer integrated into import + ML.
- Rule audit trail and DB-first analytics runtime.

Quality signals:
- Tests: 550 passing.
- Coverage: ~88% overall, with critical modules still uneven.

Known architectural constraints:
- Some runtime mappings are still partially hardcoded (UI/data mapping).
- Import/migration path still carries legacy compatibility behavior.

## 4) Source of Truth Documents

Use these first:
- Project index: `docs/project-index.qmd`
- Execution tracker: `docs/execution_plan.md`
- Domain context: `docs/context/domain.qmd`
- Importer context: `docs/context/importers.qmd`
- Services context: `docs/context/services.qmd`
- ML context: `docs/context/ml-categorization.qmd`
- Testing context: `docs/context/testing.qmd`

## 5) Development Workflow (Human + Agent)

Standard workflow:
1. Read task-relevant QMD context.
2. Add/adjust tests first for new behavior.
3. Implement minimal code changes.
4. Run targeted tests, then full test suite.
5. Update affected QMD context in same change.
6. Update `docs/execution_plan.md` when phase-level progress changes.

Mandatory principles:
- Preserve idempotency.
- Prefer deterministic transformations over opaque heuristics.
- Keep legacy compatibility unless explicitly deprecated.
- Avoid hidden behavior in UI labels; prefer canonical IDs.

## 6) Near-Term Roadmap (Phase 5)

### Phase 5A - Pipeline Robustness
- Prevent self-generated export CSVs from being re-ingested as migration inputs.
- Add explicit tests for discovery and pipeline bank filtering.
- Improve migration/pipeline branch coverage.

### Phase 5B - Configuration Unification
- Move analytics/export mapping logic to canonical config/service.
- Reduce hardcoded bank-path assumptions in UI and data access.

### Phase 5C - Observability
- Add stage timing and file-level counters in migration/pipeline logs.
- Add concise operational diagnostics command for import/migration health.

### Phase 5D - Categorization Quality
- Expand normalization dictionaries from unknown-merchant feedback.
- Add bank-specific normalization hooks with regression snapshots.

## 7) Mid-Term Roadmap (Phase 6+)

- Complete canonical account metadata-driven runtime (single mapping source).
- Optional normalized-description export mode rollout in UI/CLI.
- Incremental reprocessing flows with stronger import lineage reporting.
- Dashboard metrics from DB views only (legacy CSV read path downgraded to fallback mode).

## 8) Success Metrics

Operational:
- Re-running migration on unchanged data inserts 0 new rows.
- Import + pipeline runtime stable and explainable via logs.

Quality:
- Overall test coverage maintained above policy.
- Critical path modules (import/migration/pipeline) above 90%.

Product:
- Automatic categorization coverage improves without increasing false positives.
- Unknown-merchant duplicates reduced through normalized keys.

## 9) How to Continue Safely

When starting a new feature:
- Add a short phase item in `docs/execution_plan.md`.
- Add or update tests in `tests/`.
- Update matching QMD files before closing the task.

When touching critical paths:
- `src/generic_importer.py`
- `src/csv_to_db_migrator.py`
- `src/db_pipeline.py`
- `src/services/db_service.py`
- `src/ml_categorizer.py`

Treat changes here as high-impact and verify with full-suite tests.
