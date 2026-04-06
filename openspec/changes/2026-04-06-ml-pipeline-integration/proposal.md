# Proposal: ML Pipeline Integration

## Intent

`ImportPipelineService` carece de los campos `ml_categorizer` y `ml_confidence_threshold`. Hay 5 tests escritos contra esa API pero completamente skipped. El ML categorizer existe y funciona — solo falta el wiring.

## Scope

### In Scope
- Agregar `ml_categorizer` y `ml_confidence_threshold` al dataclass `ImportPipelineService`
- Implementar lógica ML fallback en `process_transactions()`: si rules → fallback_expense y ML disponible y confianza ≥ threshold, usar predicción ML
- Pasar `ml_categorizer` desde `generic_importer.py`
- Remover `pytestmark = skip` de `tests/test_import_pipeline_service.py`

### Out of Scope
- Cambios en `TransactionCategorizer` (src/ml_categorizer.py)
- Wiring en `import_statement.py` use case (no tiene acceso al categorizer hoy)
- UI, DB, arquitectura de capas (Finding 8)

## Approach

Agregar campos opcionales al dataclass (sin romper callers existentes). En `process_transactions()`, después de `classify_fn`, aplicar ML fallback solo cuando expense == fallback_expense. Pasar el categorizer desde `generic_importer._build_pipeline_service()`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/services/import_pipeline_service.py` | Modified | +2 campos opcionales + lógica ML fallback |
| `src/generic_importer.py` | Modified | Pasar `ml_categorizer` en `_build_pipeline_service()` |
| `tests/test_import_pipeline_service.py` | Modified | Remover `pytestmark = skip` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| ML introduce falsos positivos con baja confianza | Low | Threshold 0.5 como default; configurable |
| Callers sin ML rompen | Low | Campos opcionales con default `None` — sin cambio de comportamiento |

## Rollback Plan

`git revert` del commit — sin efecto en DB ni modelos.

## Success Criteria

- [ ] 5 tests de ML en verde (sin skip)
- [ ] Suite completa: 0 failures, cobertura ≥ 80%
- [ ] `generic_importer.py` pasa el categorizer al pipeline
