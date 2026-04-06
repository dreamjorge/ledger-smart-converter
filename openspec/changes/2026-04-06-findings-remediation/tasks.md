# Tasks: Findings Remediation

## Phase 1: RED — Failing tests (TDD first)

- [x] 1.1 `tests/test_db_service.py` — agregar test: `CanonicalTransaction.id == build_source_hash(...)` con mismos datos → deben coincidir (FALLA hoy)
- [x] 1.2 `tests/test_db_service.py` — agregar test: misma transacción importada con `/old/path/file.csv` y `/new/path/file.csv` produce el mismo hash (FALLA hoy)
- [x] 1.3 `tests/test_common_utils.py::TestRulesCoverageFromConfig` — agregar test: "Restore Electronics" → `Expenses:Other:Uncategorized` (FALLA hoy)
- [x] 1.4 `tests/test_common_utils.py::TestRulesCoverageFromConfig` — agregar test: "Restroom Supplies Co" → `Expenses:Other:Uncategorized` (FALLA hoy)
- [x] 1.5 `tests/test_common_utils.py` — agregar test: `get_statement_period("not-a-date", 15)` emite WARNING en logs (FALLA hoy — no hay logging)
- [x] 1.6 `tests/test_common_utils.py` — agregar test: `get_statement_period("2026-01-10", 15)` NO emite WARNING (FALLA hoy — comportamiento no documentado)

## Phase 2: GREEN — Implementación F3 + F1 (hash unification)

- [x] 2.1 `src/services/db_service.py:164` — cambiar `source_file` por `Path(source_file).name` en `build_source_hash()`
- [x] 2.2 `src/domain/transaction.py:26` — actualizar `CanonicalTransaction.id` para usar los mismos campos que `build_source_hash()`: reemplazar `account_id` + `normalized_description` + `rfc` por `source` (filename) + `description` (sin normalizar) — alineando ambos métodos
- [x] 2.3 `src/services/dedup_service.py:49,127` — verificar que las llamadas a `build_source_hash()` pasen `Path(source_file).name` en lugar del path completo
- [x] 2.4 `src/csv_to_db_migrator.py:49` — verificar idem

## Phase 3: GREEN — Implementación F2 (regex)

- [x] 3.1 `config/rules.yml:284` — cambiar `- rest\s*` por `- \brest\s` en la regla Restaurants
- [x] 3.2 Verificar manualmente que los patrones explícitos existentes (`rest\s*alabim`, `rest\s*carls`, `rest\s*la`) siguen matcheando con el nuevo patrón raíz

## Phase 4: GREEN — Implementación F7 (observability)

- [x] 4.1 `src/common_utils.py:104` — agregar `LOGGER = get_logger("common_utils")` si no existe; en el bloque `except ValueError` de `get_statement_period()`, agregar `LOGGER.warning("Invalid date for period calculation: %s", date_str)`
- [x] 4.2 `src/services/import_pipeline_service.py:91` — agregar log WARNING cuando `period` es vacío: `LOGGER.warning("Missing statement_period for txn %s — date: %s", canonical.id[:8], txn.date)`

## Phase 5: Verify

- [x] 5.1 `pytest tests/test_db_service.py tests/test_common_utils.py -v` — todos los tests nuevos en verde
- [x] 5.2 `pytest tests/test_csv_to_db_migrator.py tests/test_generic_importer.py -q` — sin regresiones
- [x] 5.3 `pytest -m "not slow" -q --cov=src --cov-fail-under=80` — cobertura ≥ 80%, 0 failures
