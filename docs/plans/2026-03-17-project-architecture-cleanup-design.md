# Project Architecture Cleanup Design

**Date:** 2026-03-17

## Goal

Refactor Ledger Smart Converter toward a cleaner service-oriented architecture by reducing coupling in the import pipeline, converging on consistent data-source and configuration boundaries, and aligning project documentation with the actual implemented system.

## Current State

The repository already contains most of the right architectural pieces:

- Bank-specific importers for HSBC and Santander
- A generic CLI importer
- Service-layer modules for imports, rules, analytics, DB access, and Firefly export
- SQLite persistence with deduplication and audit events
- A substantial pytest suite

The main problem is not missing capability. The problem is partial convergence:

- `src/generic_importer.py` still owns too many responsibilities
- `src/services/data_service.py` still carries CSV-era assumptions through static mappings
- Configuration knowledge is spread across `rules.yml`, `accounts.yml`, and code
- Some architecture docs still describe already-delivered features as future work

This creates maintenance drag, makes refactors riskier than necessary, and causes documentation drift for future contributors and agents.

## Recommended Approach

Use a service-boundary cleanup approach.

This is the best tradeoff because it:

- Improves maintainability without forcing an immediate big-bang persistence rewrite
- Preserves current importer behavior while creating cleaner seams
- Lets SQLite remain the preferred runtime source without breaking CSV compatibility
- Produces visible architectural progress in incremental steps

## Target Architecture

### Import Layer

Bank-specific importer modules should only parse source files and return normalized raw transaction structures.

`src/generic_importer.py` should become a thin coordinator responsible for:

- CLI argument handling
- Selecting the parser
- Invoking enrichment/categorization/persistence services
- Emitting logs and run summaries

Normalization, validation, account resolution, and categorization should move behind explicit pipeline/service functions rather than living inline in the coordinator.

### Service Layer

The service layer should become the canonical integration boundary for:

- Import orchestration
- Data loading
- Analytics aggregation
- Rules lifecycle
- DB persistence
- Firefly export generation

UI and CLI entry points should consume service APIs, not bank-specific assumptions or hardcoded file conventions.

### Data Source Model

SQLite should be the preferred operational source of truth for analytics and history.

CSV should remain supported as:

- importer output compatibility
- fallback input when DB is missing or empty
- export/interchange artifact

The code should express this clearly so there is one primary runtime model instead of two competing ones.

### Configuration Model

Configuration should distinguish clearly between:

- bank/importer settings
- canonical accounts and account metadata
- categorization rules
- optional alias/display mappings

Internal lookups should use canonical IDs. Display names should remain presentation-only.

## Improvement Areas

### 1. Import Pipeline Consolidation

Split the importer workflow into explicit phases:

1. Parse source input
2. Enrich transaction fields
3. Validate canonical records
4. Categorize and tag
5. Persist/export results

This reduces the blast radius of importer changes and makes testing much more focused.

### 2. Data Source Unification

Replace static bank/path assumptions in data access code with config-driven or metadata-driven resolution where possible.

Define one canonical read path for transaction consumers:

- DB first by default
- CSV fallback only when needed

### 3. Configuration Normalization

Clarify the contract for each config file and remove duplicated knowledge in code.

The system should not need multiple unrelated hardcoded maps to answer:

- what bank this is
- what account it belongs to
- where its data lives
- what its display label should be

### 4. Analytics Contract Cleanup

Analytics code should work against a stable input schema instead of implicit dataframe variations from different sources.

This likely means adding a normalization step at the service boundary rather than embedding source-specific assumptions inside aggregation logic.

### 5. Documentation Synchronization

QMD files and roadmap docs must reflect the current codebase state.

The project relies on these docs as authoritative context. Leaving them stale creates repeated future analysis errors.

### 6. Architectural Seam Testing

The cleanup should be protected by tests around the seams that matter most:

- importer orchestration
- DB-first/fallback loading
- config resolution
- analytics input normalization
- Firefly export from DB-backed flows

## Non-Goals

This cleanup should avoid:

- rewriting working bank parsers without a concrete defect
- removing CSV support entirely
- introducing a new framework or persistence engine
- large UI redesign work unrelated to architecture boundaries

## Risks

### Risk: Refactor churn in stable flows

Mitigation:

- add seam tests before structural changes
- keep importer parser behavior unchanged unless tests demand it

### Risk: Config migration confusion

Mitigation:

- document the config contract first
- migrate in small steps with compatibility adapters where needed

### Risk: DB and CSV behavior diverge further during cleanup

Mitigation:

- make the preferred source explicit early
- centralize fallback behavior in one service path

## Success Criteria

The cleanup is successful when:

- `generic_importer` is a thin coordinator rather than an all-in-one workflow module
- transaction loading has one clear canonical path
- configuration ownership is explicit and mostly free of duplicated bank/account logic
- analytics reads against a normalized contract
- project QMD/docs match implemented reality
- service-boundary tests protect the refactor

## Execution Strategy

The work should proceed in this order:

1. Document and lock the intended architecture
2. Add seam tests around current behavior
3. Refactor importer/data/config boundaries incrementally
4. Normalize analytics contracts
5. Update docs/QMDs alongside each completed structural change

This preserves momentum while reducing the chance of broad regressions.
