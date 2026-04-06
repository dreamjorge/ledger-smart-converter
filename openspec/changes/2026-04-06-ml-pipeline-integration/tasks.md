# Tasks: ML Pipeline Integration

## Phase 1: RED — Verify tests fail without implementation

- [x] 1.1 `tests/test_import_pipeline_service.py` — remover `pytestmark = skip` y confirmar que los 5 tests FALLAN con `TypeError` (campo no existe)

## Phase 2: GREEN — Implementation

- [x] 2.1 `src/services/import_pipeline_service.py` — agregar campos opcionales al dataclass: `ml_categorizer: Optional[Any] = None` y `ml_confidence_threshold: float = 0.5`
- [x] 2.2 `src/services/import_pipeline_service.py` — en `process_transactions()`, después de `classify_fn`, agregar bloque ML fallback: if expense == fallback_expense and ml_categorizer is not None and ml_categorizer.is_trained → predict → if confidence ≥ threshold → use ML, add `ml:predicted` tag
- [x] 2.3 `src/generic_importer.py` — aceptar `ml_categorizer` como parámetro opcional en `__init__`, almacenar en `self.ml_categorizer`, pasarlo en `_build_pipeline_service()`

## Phase 3: Verify

- [x] 3.1 `.venv/Scripts/pytest.exe tests/test_import_pipeline_service.py -v` — 5 tests en verde
- [x] 3.2 `.venv/Scripts/pytest.exe -m "not slow" -q --cov=src --cov-fail-under=80` — 712 passed, 83.51% coverage
