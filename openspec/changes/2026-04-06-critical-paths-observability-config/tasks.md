# Tasks: Critical Paths Coverage, Observability & Config Consolidation

## Phase 1: Critical Paths Coverage (tests existentes ✅, nuevo coverage ✅)

### 1.1 dedup_service coverage ✅ DONE
- [x] 15 tests passing, coverage 100%
- tests/test_dedup_service.py

### 1.2 user_service coverage
- [ ] Escribir ~15 tests para llevar user_service a 90%+
- tests/test_user_service.py (archivo nuevo o extensión)

### 1.3 data_service coverage
- [ ] Escribir ~10 tests para llevar data_service a 90%+
- tests/test_data_service.py (archivo nuevo o extensión)

## Phase 2: Observabilidad en Import Pipeline

### 2.1 Stage timing en import_pipeline_service
- [ ] Agregar timing logs por stage en process_transactions()
- Log: bank_id, input_count, output_count, warning_count, stage_durations

### 2.2 Contadores por archivo en generic_importer
- [ ] Emitir log con archivo procesado, rows insertadas, tiempo total
- Log estructurado: input_file, row_count, duration_seconds

## Phase 3: Config Consolidation

### 3.1 Unificar lectura de accounts.yml en rules_config_service
- [ ] rules_config_service expone helper load_accounts_config() público
- [ ] data_service._load_accounts_config() delega a rules_config_service

### 3.2 Validar contratos
- [ ] Verificar que rules_config_service cubre toda la lógica de parseo de config/
- [ ] Eliminar duplicación en account_mapping si existe
