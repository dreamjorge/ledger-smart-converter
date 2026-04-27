# Deuda Técnica: catch-up con origin/main

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Actualizar la branch `feature/db-classification-firefly-improvements` para que incorpore las mejoras arquitectónicas ya entregadas en `origin/main`, y luego ejecutar la limpieza de deuda residual.

**Architecture:** Tres fases — (1) absorbed merged features (traer lo que main ya tiene), (2) cleanup de deuda técnica específica, (3) verificación final.

**Tech Stack:** Python 3.8+, pytest, pandas, sqlite3, Clean Architecture

---

## Estado Real: Nuestra branch vs origin/main

| Aspecto | Our Branch (behind) | origin/main (ahead) |
|---------|---------------------|---------------------|
| `flet_prototype.py` | Old prototype, 189 lines | ELIMINADO → `flet_app.py` nuevo |
| `CanonicalTransaction` | 10 fields | 17 fields (transaction_type, category, tags, notes, is_synced...) |
| Arquitectura | Capas mezcladas | Clean Architecture (application/ports, infrastructure/adapters) |
| `ImportPipelineService` | Params individuales | `AppConfiguration` + `BankConfig` typed |
| ML | Separate call post-import | Integrado en pipeline con confidence threshold |
| Dedup | Solo `insert_transaction` | `insert_transactions_batch`, `upsert_transaction`, `transaction_exists` |
| New services | No | `dedup_service`, `rules_config_service`, `manual_entry_service`, `ui_service`, `user_service` |
| `build_source_hash` | Sin `canonical_account_id` | Incluye `canonical_account_id` |
| User management | No | `user_service.py` con bcrypt + prefs.json |
| Clean Architecture | No | `TransactionRepository` port + `SqliteTransactionRepository` adapter |
| Config models | No | `domain/config_models.py` con typed dataclasses |

**Conclusión**: Nuestra branch está ~30+ commits detrás en arquitectura. No es solo deuda técnica, es deuda de features.

---

## Phase 1: Absorber mejoras de origin/main

### Task 1.1: Rebase/Merge origin/main

**Files:**
- Merge: `origin/main` into current branch
- Modify: conflict resolution en archivos que cambiaron en ambos lados

**Step 1: Verificar estado actual**

```bash
git status
git log --oneline -5
```

**Step 2: Merge origin/main**

```bash
git merge origin/main
```

Expected:可能有 conflictos en:
- `src/domain/transaction.py` (nuevos campos)
- `src/services/import_pipeline_service.py` (cambio de firma)
- `src/services/db_service.py` (nuevos métodos)
- `src/generic_importer.py` (cambio en ML retrain)

**Step 3: Resolver conflictos uno por uno**

Para cada conflicto,优先保留 la versión de origin/main (es la más nueva):
- CanonicalTransaction → usar la de main (más campos)
- ImportPipelineService → usar la de main (AppConfiguration typed)
- db_service.py → usar la de main (más métodos)
- generic_importer.py → usar la de main (ML integration)

**Step 4: Run tests after merge**

```bash
python -m pytest -m "not slow" -q --tb=short
```

Expected: PASS or manageable failures

**Step 5: Commit merge**

```bash
git add -A
git commit -m "merge: absorb origin/main architectural improvements"
```

---

### Task 1.2: Eliminar `flet_prototype.py` (si aún existe post-merge)

**Files:**
- Delete: `src/flet_prototype.py` (si survived the merge)
- Modify: `docs/project-index.qmd`

**Step 1: Check if file exists**

```bash
ls src/flet_prototype.py 2>/dev/null && echo "EXISTS" || echo "GONE"
```

**Step 2: If exists, delete it**

```bash
rm src/flet_prototype.py
git rm src/flet_prototype.py
git commit -m "chore: remove legacy flet prototype"
```

---

## Phase 2: Limpieza de deuda residual post-merge

After Phase 1, several debt items from our original list will be ALREADY FIXED by the merge:

| Original Debt | Status after Phase 1 |
|--------------|----------------------|
| D1: import_service + import_pipeline overlap | FIXED (main tiene mejor separación con AppConfiguration) |
| D3: ML retrain coupling | FIXED (main integra ML en pipeline con confidence threshold) |
| D5: db_pipeline coverage | FIXED automatically by expanded test suite in main |
| D6: _ensure_transactions_columns called twice | FIXED in main's db_service.py |

**Remaining debt to address explicitly:**

### Task 2.1: coverage de data_service.py

**Files:**
- Modify: `tests/test_data_service.py`
- Test: `tests/test_data_service.py`
- Target: Coverage > 85%

**Step 1: Run coverage check**

```bash
python -m pytest tests/test_data_service.py --cov=src/services/data_service --cov-report=term-missing
```

**Step 2: Add tests for uncovered helper functions**

```python
def test_supported_bank_ids_from_empty_config(tmp_path):
    """_supported_bank_ids returns legacy banks when config is empty."""
    from data_service import _supported_bank_ids
    result = _supported_bank_ids(tmp_path / "accounts.yml")
    assert "hsbc" in result
    assert "santander" in result

def test_resolve_csv_output_path_returns_none_for_unknown():
    from data_service import _resolve_csv_output_path
    result = _resolve_csv_output_path("unknown:canonical", {"bank_ids": []})
    assert result is None
```

**Step 3: Run and verify**

```bash
python -m pytest tests/test_data_service.py --cov=src/services/data_service --cov-fail-under=85
```

**Step 4: Commit**

```bash
git add tests/test_data_service.py src/services/data_service.py
git commit -m "test: raise data_service coverage to 85%"
```

---

### Task 2.2: coverage de db_pipeline.py

**Files:**
- Modify: `tests/test_db_pipeline.py`
- Test: `tests/test_db_pipeline.py`
- Target: Coverage > 85%

**Step 1: Run coverage**

```bash
python -m pytest tests/test_db_pipeline.py --cov=src/db_pipeline --cov-report=term-missing
```

**Step 2: Add test for run_db_pipeline main execution**

```python
def test_run_db_pipeline_returns_expected_keys(monkeypatch):
    """run_db_pipeline returns dict with migration and exports keys."""
    from db_pipeline import run_db_pipeline

    # Mock dependencies
    monkeypatch.setattr("db_pipeline.migrate_csvs_to_db", lambda **kw: {"tables": {"transactions": 10}})
    monkeypatch.setattr("db_pipeline.DatabaseService", lambda **kw: MagicMock())
    monkeypatch.setattr("db_pipeline.export_firefly_csv_from_db", lambda **kw: 5)

    result = run_db_pipeline(
        db_path=Path("/tmp/test.db"),
        data_dir=Path("/tmp/data"),
    )

    assert isinstance(result, dict)
    assert "migration" in result
    assert "exports" in result
```

**Step 3: Run and verify**

```bash
python -m pytest tests/test_db_pipeline.py --cov=src/db_pipeline --cov-fail-under=85
```

**Step 4: Commit**

```bash
git add tests/test_db_pipeline.py src/db_pipeline.py
git commit -m "test: raise db_pipeline coverage to 85%"
```

---

### Task 2.3: Aislar import_service.py si aún tiene lógica duplicada

**Files:**
- Modify: `src/services/import_service.py`
- Test: `tests/test_import_service.py`

**Step 1: Read import_service.py post-merge**

```bash
head -60 src/services/import_service.py
```

**Step 2: Verify responsibilities**

After the merge with main, `import_service.py` debería tener:
- `save_uploaded_file()`
- `resolve_output_paths()`
- `run_import_script()` (subprocess runner)
- `copy_csv_to_analysis()`
- `get_banks_from_config()` (nuevo de main)
- `get_csv_last_updated()`

Si tiene lógica de orquestación que ya está en `ImportPipelineService`,考虑 moverla.

**Step 3: Commit cualquier cleanup**

```bash
git add src/services/import_service.py
git commit -m "refactor: import_service cleanup post-merge"
```

---

## Phase 3: Verificación final

### Task 3.1: Run full test suite

**Files:**
- Test: `python -m pytest -m "not slow" -q --tb=short`
- Verify: 598+ tests passing

**Step 1: Run fast suite**

```bash
python -m pytest -m "not slow" -q --tb=no
```

Expected: All pass

**Step 2: Run with coverage**

```bash
python -m pytest tests/ --cov=src --cov-fail-under=85 -q
```

Expected: PASS

**Step 3: Commit final verification**

```bash
git add -A
git commit -m "test: full suite passing after debt cleanup"
```

---

## Resumen de Dependencies

```
Phase 1 (sequential):
  Task 1.1: Merge origin/main → TASKS 1.2
  Task 1.2: Delete flet_prototype → Phase 2

Phase 2 (can parallel after Phase 1):
  Task 2.1: data_service coverage
  Task 2.2: db_pipeline coverage
  Task 2.3: import_service cleanup

Phase 3 (sequential after Phase 2):
  Task 3.1: Full verification
```

## Métricas Esperadas

| Metric | Antes (our branch) | Después |
|--------|--------------------|---------|
| Arquitectura | Old (mixed layers) | Clean Architecture (main's) |
| CanonicalTransaction fields | 10 | 17 |
| New services | 0 | 5 (dedup, user, rules_config, manual_entry, ui_service) |
| flet_prototype.py | 189 líneas | ELIMINADO |
| Coverage data_service | 80% | 85%+ |
| Coverage db_pipeline | 68% | 85%+ |
| Test count | 598 | 650+ (main added many tests) |
| ML integration | Post-import coupling | Integrated with confidence threshold |

---

## Commands de Verificación Rápida

```bash
# Check we're on the right branch
git branch --show-current

# Check we're aligned with origin/main
git log --oneline origin/main..HEAD  # should be empty or few commits ahead

# Run full suite
python -m pytest -m "not slow" -q --tb=no

# Check for flet_prototype
ls src/flet_prototype.py 2>/dev/null && echo "STILL EXISTS" || echo "GONE"
```