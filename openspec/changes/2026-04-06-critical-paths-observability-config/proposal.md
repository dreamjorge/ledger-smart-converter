# Proposal: Critical Paths Coverage, Observability & Config Consolidation

## Intent

Tres deudas técnicas que limitan la confiabilidad operativa y la mantenibilidad del proyecto:

1. **Coverage gaps en critical paths**: `dedup_service` (60.7%), `user_service` (71.1%), `data_service` (76.5%) están por debajo del umbral 90% que el roadmap define para caminos críticos.
2. **Observabilidad insuficiente**: Los flujos de import, migration y export carecen de stage-timing, contadores por archivo, y logging que permita auditar o debuggear sin leer código.
3. **Fragmentación de configuración**: `rules.yml`, `accounts.yml`, y los servicios que los leen (`rules_config_service`, `data_service`, `account_mapping`) no tienen un contrato unificado, generando duplicación y potencial desalineación.

## Scope

### In Scope
- Agregar 20-25 tests para llevar `dedup_service` de 60.7% → 90%+
- Agregar 15-18 tests para llevar `user_service` de 71.1% → 90%+
- Agregar 10-12 tests para llevar `data_service` de 76.5% → 90%+
- Agregar stage-timing y contadores de archivo en `import_pipeline_service` y `generic_importer`
- Agregar logging estructurado en DB-first path (data_service, db_service)
- Unificar la lectura de `rules.yml` en `rules_config_service` como único punto de entrada; eliminar lógica duplicada en `data_service._load_accounts_config()` y `account_mapping`

### Out of Scope
- Nuevos features de ML o UI
- Cambios en schema de SQLite
- Refactor de importers existentes

## Approach

**TDD first**: escribir tests hasta alcanzar coverage target antes de tocar implementación. Para observabilidad, agregar logging en puntos estratégicos del pipeline existente. Para configuración, extraer la lógica de parseo de YAML a un helper compartido en `rules_config_service`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/services/dedup_service.py` | Modified | +20 tests → coverage 90%+ |
| `src/services/user_service.py` | Modified | +15 tests → coverage 90%+ |
| `src/services/data_service.py` | Modified | +10 tests → coverage 90%+ |
| `src/services/rules_config_service.py` | Modified | Unificar parseo YAML, exponer helper compartido |
| `src/services/import_pipeline_service.py` | Modified | Agregar stage-timing logs |
| `src/generic_importer.py` | Modified | Agregar contadores por archivo |
| `src/services/data_service.py` | Modified | Delegar parseo accounts.yml a rules_config_service |
| `config/rules.yml` | Modified | Ningún cambio funcional |
| `config/accounts.yml` | Modified | Ningún cambio funcional |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests nuevos rotos por dependencia de estado global en prefs.json | Low | Mockear `_prefs_path()` con pytest fixture tmp_path |
| Duplicar lógica de parsing de accounts.yml | Low | Extraer a función pura en rules_config_service antes de refactorar |
| Logging verbose rompe caplog en tests existentes | Low | Usar logger.setLevel(logging.INFO) en conftest; verificar que tests pasan |

## Rollback Plan

`git checkout -- <files>` revierte todos los cambios sin efecto en DB ni modelos. Los tests nuevos que no compilan se ignoran en CI hasta corregirse.

## Success Criteria

- [ ] `dedup_service` coverage ≥ 90% (actualmente 60.7%)
- [ ] `user_service` coverage ≥ 90% (actualmente 71.1%)
- [ ] `data_service` coverage ≥ 90% (actualmente 76.5%)
- [ ] `import_pipeline_service` y `generic_importer` emiten stage-timing en logs
- [ ] `rules_config_service` es el único punto de lectura de `rules.yml` y `accounts.yml`
- [ ] Suite completa: 721 + ~50 tests, 0 failures, cobertura total ≥ 85%
