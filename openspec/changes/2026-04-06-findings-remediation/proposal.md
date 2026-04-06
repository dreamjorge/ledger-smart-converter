# Proposal: Findings Remediation

## Intent

Corregir 4 bugs verificados con evidencia en código que afectan la integridad de datos (deduplicación rota), exactitud de categorización (regex shadowing), y observabilidad (fallos silenciosos).

## Scope

### In Scope
- **F3**: Normalizar `source_file` en hash de dedup — usar solo filename, no path absoluto
- **F1**: Unificar dos métodos de hash (`CanonicalTransaction.id` vs `build_source_hash`) en uno solo
- **F7**: Agregar logging de warning en `get_statement_period()` cuando el date parsing falla
- **F2**: Acotar regex `rest\s*` → `\brest\b` para evitar false positives en categorización

### Out of Scope
- Migración retroactiva de hashes existentes en la DB (datos actuales son consistentes internamente)
- Refactor de arquitectura UI → DB (Finding 8, esfuerzo alto, sesión separada)
- Threshold de coverage CI (Finding 6, cambio de documentación)

## Approach

1. **F3 → F1 (hash)**: Cambiar `build_source_hash()` para usar `Path(source_file).name` en lugar del path completo. Luego alinear `CanonicalTransaction.id` para que use los mismos campos que `build_source_hash()` — o deprecar `build_source_hash()` y hacer que todos los callers usen `transaction.id`. El repositorio ya usa `transaction.id` como source canónico; `csv_to_db_migrator.py` y `dedup_service.py` usan `build_source_hash()` — hay que unificar.
2. **F7 (statement_period)**: En `get_statement_period()`, agregar `LOGGER.warning(...)` cuando retorna `""`. En `import_pipeline_service.py`, loggear también si el período queda vacío.
3. **F2 (regex)**: Cambiar `rest\s*` → `\brest\s` con test de regresión para "Restore Electronics" y "Restroom Supplies".

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/transaction.py:26` | Modified | `CanonicalTransaction.id` — alinear campos con `build_source_hash` |
| `src/services/db_service.py:155` | Modified | `build_source_hash()` — usar `Path.name` para `source_file` |
| `src/infrastructure/adapters/sqlite_transaction_repository.py` | Verify | Ya usa `transaction.id`; verificar consistencia post-unificación |
| `src/csv_to_db_migrator.py` | Modified | Actualizar llamadas a `build_source_hash()` si se depreca |
| `src/services/dedup_service.py` | Verify | Usa `build_source_hash()` — verificar callers |
| `src/common_utils.py:104` | Modified | `get_statement_period()` — agregar logging |
| `src/services/import_pipeline_service.py:91` | Modified | Loggear period vacío |
| `config/rules.yml:284` | Modified | `rest\s*` → `\brest\s` |
| `tests/test_common_utils.py` | Modified | Tests de regresión para F2 y F7 |
| `tests/test_db_service.py` | Modified | Test de dedup con path relativo vs absoluto |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cambio de hash invalida dedup de datos existentes | Low | Los datos actuales usan `transaction.id`; `build_source_hash` solo se usa en migración — hashes nuevos no colisionan con existentes |
| Regex más estricto rompe categorización existente | Low | Tests de regresión en `TestRulesCoverageFromConfig` antes del cambio (TDD) |
| Logging excesivo en producción | Low | Level WARNING, no ERROR — solo cuando hay problema real |

## Rollback Plan

- `config/rules.yml`: `git revert` del commit específico — sin efecto en DB
- Hash changes: `git revert` — no hay migración de datos; los hashes nuevos no se generan hasta el próximo import
- Logging: `git revert` — no hay efecto en datos

## Dependencies

- Ninguna dependencia externa. Todo en src/ y config/.

## Success Criteria

- [ ] `build_source_hash()` y `CanonicalTransaction.id` producen el mismo hash para la misma transacción
- [ ] Reimportar el mismo archivo desde distintos paths no genera duplicados
- [ ] "Restore Electronics" y "Restroom Supplies" NO se categorizan como Restaurants
- [ ] `pytest tests/test_common_utils.py::TestRulesCoverageFromConfig` — 15+ tests passing
- [ ] `get_statement_period("invalid-date", 15)` emite WARNING en los logs
- [ ] `pytest -m "not slow" -q` — sin regresiones, cobertura ≥ 80%
