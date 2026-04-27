# Project Improvement Plan — SDD

> **For Claude:** Use sdd-propose, sdd-design, sdd-tasks workflow for implementation.

**Goal:** Fortalecer la base del proyecto con cobertura de tests en módulos críticos, mejoras de observabilidad, y closure de deuda técnica identificada en el análisis de arquitectura.

**Architecture:** El proyecto post-merge tiene Clean Architecture (application/ports + infrastructure/adapters), ML integrado en pipeline, y typed config models. El foco de este plan es elevar coverage, consolidar deuda residual, y preparar la base para features futuros.

**Tech Stack:** Python 3.8+, pytest, pandas, sqlite3, scikit-learn, Streamlit, YAML

---

## Contexto: Lo que absorbió el merge

Después de ejecutar `merge origin/main`, la branch incorporó:

```
✅ Clean Architecture: application/ports (TransactionRepository, FireflySyncPort, etc.)
✅ infrastructure/adapters: SqliteTransactionRepository, YamlRulesRepository, etc.
✅ domain/config_models.py: BankConfig, AppConfiguration, CategorizationRule (typed)
✅ ML integrado en ImportPipelineService (confidence threshold configurable)
✅ CanonicalTransaction: 17 fields (transaction_type, category, tags, notes, is_synced, user_id)
✅ 5 nuevos servicios: dedup_service, rules_config_service, manual_entry_service, ui_service, user_service
✅ user_service: bcrypt PIN protection + prefs.json
✅ flet_app.py (nuevo,取代 flet_prototype)
✅ Banamex JOY parser + parser_factory
✅ 150 files changed, +13,033 líneas
✅ 757 tests, 85.70% coverage
```

---

## Deuda Técnica Identificada en el Análisis

### 🔴 Alta Prioridad

| ID | Item | Ubicación | Status | Esfuerzo |
|----|------|-----------|--------|----------|
| DT-1 | description_normalizer coverage 72% (bajo mínimo 85%) | `src/description_normalizer.py` | ❌ | Medium |
| DT-2 | db_pipeline main() CLI coverage 68% | `src/db_pipeline.py:59-76` | ⚠️ | Low |
| DT-3 | data_service coverage 88.70% con 20 líneas sin cover | `src/services/data_service.py` | ⚠️ | Low |

### 🟡 Media Prioridad

| ID | Item | Ubicación | Status | Esfuerzo |
|----|------|-----------|--------|----------|
| DT-4 | common_utils.py tiene clasificaciones embebidas en classify() | `src/common_utils.py` | ⚠️ | Medium |
| DT-5 | generic_importer.py tiene lógica de categorización duplicada | `src/generic_importer.py` | ⚠️ | Medium |
| DT-6 | settings global evaluated at import time | `src/settings.py` | ⚠️ | Low |

### 🟢 Baja Prioridad

| ID | Item | Ubicación | Status | Esfuerzo |
|----|------|-----------|--------|----------|
| DT-7 | No hay validación FK para `canonical_account_id` | `src/domain/transaction.py` | ⚠️ | Low |
| DT-8 | Hardcoded path assumptions en db_pipeline | `src/db_pipeline.py` | ⚠️ | Low |

---

## Mejoras Arquitectónicas Sugeridas

### 1. Description Normalizer — Coverage a 85%+

**Problema:** `description_normalizer.py` tiene 72% coverage con 19 líneas sin cover.

**Archivos:**
- `src/description_normalizer.py`
- `tests/test_description_normalizer.py`

**Análisis de coverage:**
```
src/description_normalizer.py   68     19  72.06%   14-25, 49, 55, 57, 59, 62-63, 65-66, 68-69, 79-81, 87, 94
```

**Líneas sin cover:** 14-25 (normalize_description core logic), 49-81 (regex compilation + normalization helpers)

**Próximo paso:** Escribir tests unitarios para las funciones helper que no se testean directamente (e.g., `_compile_patterns`, `_apply_normalizations`)

---

### 2. Observabilidad en Pipeline de Import

**Problema:** No hay tracing de stages en el import pipeline. Cuando un import falla o es lento, no hay manera fácil de identificar el bottleneck.

**Archivos afectados:**
- `src/services/import_pipeline_service.py`
- `src/services/analytics_service.py`

**Estado actual:** El pipeline ya tiene stage timing logs (líneas 107-114), pero no hay métricas estructuradas para dashboard.

**Próximo paso:** Crear un servicio de métricas simple que capture:
- Tiempo por stage (normalize, classify, build)
- Count de transacciones procesadas vs. fallidas vs. categorizadas
- Exportar a SQLite o dashboard

---

### 3. Firefly API Sync (Futuro)

**Problema:** Exportamos CSV a Firefly pero no hay sync bidireccional.

**Estado:** `src/application/ports/firefly_sync_port.py` ya existe en el merge, pero el sync real no está implementado.

**Arquitectura propuesta:**
```
firefly_sync_port.py (port interface)
    └── firefly_api_adapter.py (infrastructure adapter)
            └── sync_transactions_to_firefly use case
```

**Próximo paso:** Implementar `sync_transactions_to_firefly.py` use case que:
1. Marque transacciones como `is_synced = True` después de exportar
2. Maneje reintentos con backoff exponencial
3. Logue eventos de sync en `audit_events`

---

### 4. Banamex Parser — Completar Coverage

**Problema:** Banamex JOY parser es nuevo (233 líneas) pero tiene PDF tests que saltan si no hay PDF real disponible.

**Archivos:**
- `src/infrastructure/parsers/banamex_parser.py`
- `tests/infrastructure/parsers/test_banamex_parser.py`

**Estado actual:**
```
SKIPPED tests/infrastructure/parsers/test_banamex_parser.py — Real Banamex PDF not available
```

**Próximo paso:** Agregar fixtures de PDF de Banamex (sin datos sensibles) paratesting completo, o crear parser tests que no dependan del PDF real usando mock de `pdfplumber`.

---

### 5. UI Service Consolidation

**Problema:** Hay lógica de UI duplicada entre Streamlit y Flet. `ui_service.py` (175 líneas) tiene helpers de gráficos, pero no está claro cuál es el contrato entre UIs.

**Archivos:**
- `src/services/ui_service.py`
- `src/ui/flet_ui/*.py`
- `src/ui/pages/analytics_page.py`

**Próximo paso:** Definir el contrato de `ui_service.py`:
- ¿Qué formatting helpers son compartidos?
- ¿Los gráficos (plotly) deben generarse en el service o en la UI?
- ¿Hay estado que debe persistir entre UIs?

---

## Plan de Implementación Sugerido (Task Groups)

### Group A: Coverage Elevation (1-2 días)

```
Task A.1: description_normalizer coverage 72% → 85%+
Task A.2: common_utils coverage gap analysis (si hay líneas sin cover)
Task A.3: Verificar que ningún módulo crítico esté bajo 85% post-changes
```

### Group B: Observabilidad (1 día)

```
Task B.1: Instrumentar import_pipeline con métricas estructuradas
Task B.2: Crear dashboard de métricas de import (success rate, timing, categorization)
Task B.3: Agregar logging de auditoría para sync de Firefly (cuando se implemente)
```

### Group C: Debt Cleanup (1 día)

```
Task C.1: Eliminar código duplicado en generic_importer (si classify() está duplicado)
Task C.2: Revisar canonical_account_id validation
Task C.3: Actualizar plan_mejoras.md con estado post-merge
```

### Group D: Firefly Sync (2-3 días)

```
Task D.1: Implementar firefly_sync_port con mock de API
Task D.2: Implementar sync_transactions_to_firefly use case
Task D.3: Agregar tests de integración con mock de Firefly API
Task D.4: Actualizar docs de configuración con FIREFLY_URL/TOKEN
```

---

## Criterios de Aceptación

| Métrica | Target | Actual |
|---------|--------|--------|
| Coverage total | ≥ 85% | 85.70% ✅ |
| description_normalizer | ≥ 85% | 72% ❌ |
| db_pipeline | ≥ 85% | 68% ⚠️ |
| data_service | ≥ 85% | 88.70% ✅ |
| Tests | ≥ 750 | 757 ✅ |
| Módulos sin cover en critical path | 0 | 1 ❌ (description_normalizer) |

---

## Referencias

- Análisis de arquitectura: `docs/plans/2026-04-26-debt-cleanup.md`
- Estado del merge: `git log origin/main..HEAD`
- Plan de mejoras legado: `docs/plan_mejoras.md`
- QMD context: `docs/context/*.qmd`

---

## Para Ejecución Futura

**Comando de verificación rápido:**
```bash
python -m pytest -m "not slow" -q --cov=src --cov-fail-under=85 --tb=no
```

**Verificar coverage por módulo:**
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing -q --tb=no | grep -E "(data_service|db_pipeline|description_normalizer|common_utils)"
```