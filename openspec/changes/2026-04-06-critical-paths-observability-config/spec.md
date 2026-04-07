# Spec: Critical Paths Coverage, Observability & Config Consolidation

## Context

Coverage de tres servicios críticos está por debajo del umbral 90% definido en el roadmap:
- `dedup_service`: 60.7% → 100% ✅ (ya resuelto con 13 tests nuevos)
- `user_service`: 71.1% (necesita ~15 tests adicionales)
- `data_service`: 76.5% (necesita ~10 tests adicionales)

## Scenario: Coverage en dedup_service

### Given un DatabaseService inicializado con una cuenta
### When se llama check_and_insert_batch con filas que tienen hashes existentes en DB
### Then las filas son marcadas como duplicates y no insertadas

### Given un row existente en DB  
### When se llama resolve_duplicates con decisión "overwrite"
### Then el row existente es actualizado y counts["overwritten"] = 1

### Given un row existente en DB
### When se llama resolve_duplicates con decisión "keep_both"
### Then un nuevo row con source_file modificado es insertado y counts["kept_both"] = 1

### Given un row existente en DB
### When se llama resolve_duplicates con decisión "skip" o decisión desconocida
### Then nada se inserta y counts["skipped"] = 1

## Scenario: Coverage en user_service

### Given un prefs.json vacío
### When se llama get_active_user()
### Then retorna None

### Given un prefs.json con active_user configurado
### When se llama set_active_user(None)
### Then el campo active_user es removido del prefs.json

### Given un DatabaseService con tabla users
### When se llama list_users() en una DB vacía
### Then retorna lista vacía

### Given un DatabaseService con tabla users
### When se llama create_user() con user_id duplicado
### Then retorna False y no se crea usuario

### Given un DatabaseService con un usuario con password_hash
### When se llama verify_password() con password correcto
### Then retorna True

### Given un DatabaseService con un usuario sin password_hash (NULL)
### When se llama verify_password() con cualquier password
### Then retorna True (open access)

## Scenario: Coverage en data_service

### Given un accounts.yml con canonical_accounts definidos
### When se llama load_transactions_from_csv con bank_id válido
### Then retorna DataFrame con datos parseados

### Given un accounts.yml vacío
### When se llama load_transactions_from_csv con bank_id desconocido
### Then lanza ValueError

### Given un archivo CSV que no existe
### When se llama load_transactions_from_csv
### Then retorna DataFrame vacío

## Scenario: Observabilidad en import_pipeline

### Given un import_pipeline con transacciones procesadas
### When se completan todas las transacciones
### Then el log emite timing aggregate con input_count, output_count, warning_count

## Scenario: Config consolidation en rules_config_service

### Given un rules.yml con banks, defaults, merchant_aliases
### When se llama load_expense_categories() o load_bank_display_names()
### Then retorna datos estructurados sin duplicar lógica de parseo

### Given que data_service necesita la configuración de accounts
### When se llama _load_accounts_config
### Then delega a rules_config_service como único punto de entrada
