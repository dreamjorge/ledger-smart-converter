# Plan de mejoras (propuesta ejecutable)

Este plan busca tres metas: **despliegue claro**, **unificación de cuentas**, y **generación consistente de base de datos** para el dashboard y para exportación a Firefly III. El objetivo adicional es pasar de una visión conceptual a una **hoja de ruta accionable** con entregables, criterios de aceptación y riesgos.

---

## Estado actual (actualizado)

### Completado
- [x] Capa de confiabilidad en importador: validación de transacciones/tags, errores tipados y logging estructurado.
- [x] Flags operativos en CLI de importación: `--strict`, `--dry-run`, `--log-json`.
- [x] Escrituras atómicas para salidas de importación.
- [x] Scripts bash añadidos: `scripts/setup_env.sh`, `scripts/run_web.sh`, `scripts/run_import.sh`.
- [x] Healthcheck de entorno: `src/healthcheck.py`.
- [x] Configuración por entorno: `src/settings.py` + `.env.example`.
- [x] Refactor de arquitectura UI: `src/web_app.py` como router + páginas en `src/ui/pages/`.
- [x] Capa de servicios: `src/services/import_service.py`, `src/services/rule_service.py`, `src/services/analytics_service.py`.
- [x] Workflow seguro de reglas: staging en `config/rules.pending.yml`, detección de conflictos, merge con respaldo en `config/backups/`.
- [x] Suite de pruebas ampliada (14 tests pasando localmente).
- [x] CI automatizado en GitHub Actions: `.github/workflows/ci.yml`.

### Pendiente (siguiente tramo)
- [ ] Modelo canónico completo de cuentas (`account_id`) y alias dedicados en archivos separados.
- [ ] Persistencia intermedia (SQLite/DuckDB) con migración desde CSVs.
- [ ] Exporter Firefly y dashboard leyendo desde vistas de DB.
- [ ] Auditoría avanzada de cambios de reglas y re-procesos incrementales.

---

## Principios de diseño
- **Observabilidad primero**: cada etapa deja logs y métricas mínimas para auditoría.
- **Idempotencia**: re-procesar un archivo no duplica data (hash de fuente).
- **Extensibilidad**: nuevos bancos/formatos se integran por configuración.
- **Compatibilidad**: mantener CSVs actuales durante la transición.

## 1) Despliegue (documentación + automatización)

**Corto plazo (0-2 semanas)**
- Documentar despliegue local y en servidor (Linux/Windows) con Streamlit.
- Checklist de pre-requisitos (Python, Tesseract, deps) y rutas conocidas por SO.
- Plantillas de `.env`/`config` para rutas de OCR y directorios de datos.
- Sección de **troubleshooting** (OCR, encoding, permisos en rutas).

**Mediano plazo (2-6 semanas)**
- Script de instalación multiplataforma (PowerShell + bash) para instalar dependencias.
- Script de arranque en modo servidor (`--server.address 0.0.0.0`).
- Guía de despliegue en VPS (systemd o supervisor) y recomendaciones de backups.
- Healthcheck básico (endpoint o script) para validar OCR, DB y rutas.

**Entregables y aceptación**
- README actualizado con pasos de instalación/arranque por SO.
- Scripts con salida clara y codes de error.
- Un playbook de despliegue con recuperación ante fallos.

## 2) Unificación de cuentas (modelo canónico)

**Objetivo:** presentar una vista homogénea de cuentas, sin importar si provienen de HSBC, Santander u otras fuentes.

**Propuesta técnica**
- Definir un **`account_id` canónico** (ej. `credit_card:santander_likeu`, `credit_card:hsbc`).
- Introducir un **alias map** (por nombre de banco o CSV) → `account_id`.
- Mantener **metadatos de cuenta** (tipo, moneda, banco, cierre, tags por defecto).
- En `rules.yml`, separar **nombres de cuenta visibles** vs. **IDs internos**.
- Normalizar tags de cuenta (`card:*`, `bank:*`, `currency:*`).

**Detalle de configuración sugerida**
- `config/accounts.yml`: catálogo canónico de cuentas y metadatos.
- `config/aliases.yml`: mapeo de alias externos → `account_id`.
- Actualizar `rules.yml` para referenciar `account_id` y `display_name`.

**Resultados esperados**
- Dashboard unificado con filtros por cuenta/banco/categoría.
- Exportación consistente a Firefly con un mapeo único de cuentas.

## 3) Generación de base de datos (dashboard + Firefly)

**Problema actual:** la app trabaja sobre CSV dispersos; es difícil unificar y comparar histórico o re-procesos.

**Propuesta:** introducir un **almacenamiento intermedio** (SQLite o DuckDB) con un esquema consistente.

### Esquema sugerido (SQLite)
- `transactions` (tabla principal)
  - `id`, `date`, `amount`, `currency`, `merchant`, `description`
  - `account_id`, `bank_id`, `statement_period`, `category`, `tags`
  - `source_file`, `source_hash`, `created_at`, `updated_at`
- `accounts`
  - `account_id`, `display_name`, `type`, `bank_id`, `closing_day`, `currency`
- `rules`
  - `rule_id`, `regex`, `category`, `tags`, `priority`, `enabled`
- `imports`
  - `import_id`, `bank_id`, `source_file`, `processed_at`, `status`

### Reglas de deduplicación
- `source_hash = sha256(bank_id + source_file + date + amount + merchant)`
- Unicidad por `(source_hash)` para evitar duplicados en re-procesos.
- Campo `import_id` para rastrear lote de carga.

### Flujo de datos (ETL)
1. **Ingesta**: CSV/XML/PDF → `transactions_raw`.
2. **Normalización**: limpieza y enriquecimiento → `transactions`.
3. **Reglas + ML**: categorización y tags → `transactions`.
4. **Exports**:
   - Vista `firefly_export` con columnas exactas requeridas.
   - Vista `dashboard_metrics` agregada por periodos/categorías.

**Beneficios**
- Historial consistente, evita duplicados mediante `source_hash`.
- Dashboard más rápido con consultas agregadas.
- Exportación Firefly estable y auditable (log de importes).

**Entregables y aceptación**
- Migración de CSVs existentes a la DB sin pérdida de campos.
- Exporter Firefly consume vistas en DB, no CSV directo.
- Se puede re-procesar un mismo PDF/CSV sin duplicar filas.

## 4) Hoja de ruta sugerida (prioridades)

**Fase 1 (rápida, 1-2 semanas)**
- Documentación de despliegue + plantilla de config.
- Mapa canónico de cuentas + alias.
- Unificación de rutas de salida en `data/`.
- Checklist de validación por banco (HSBC/Santander).

**Fase 2 (2-6 semanas)**
- Base de datos SQLite con migración de CSV existentes.
- Exporter Firefly desde DB.
- Dashboard leyendo vistas agregadas desde DB.
- Registro de importaciones y auditoría básica.

**Fase 3 (6+ semanas)**
- UI para gestionar cuentas/rules.
- Re-procesos incrementales y auditoría de cambios.
- Sincronización automática con Firefly (opcional vía API).
- Reporte mensual automático (PDF/CSV) con KPIs.

---

## Métricas de éxito
- Tiempo de setup nuevo usuario < 30 minutos.
- 0 duplicados en re-importaciones durante un mes de uso.
- 90%+ de transacciones categorizadas automáticamente.

## Riesgos y mitigaciones
- **OCR inconsistente** → mantener XML/XLSX como fallback.
- **Reglas desalineadas** → versionar reglas con `rules.yml` y registrar cambios.
- **Migración de datos** → scripts idempotentes y backups previos.
