# Add New Bank Importer

Add a new bank importer for: $ARGUMENTS

Follow the standard workflow from `docs/context/importers.qmd`:

1. **Create importer file** `src/import_<bank>_firefly.py`:
   - Import `CanonicalTransaction` from `domain.transaction`
   - Implement `process_<bank>_statement(file_path: Path) -> List[Dict]`
   - Use `parse_mx_date()` from `pdf_utils` for date parsing
   - Use `parse_amount_str()` for amount normalization
   - Use `determine_statement_period()` from `common_utils` for period tagging
   - Add structured logging via `from logging_config import get_logger`

2. **Add config section** in `config/rules.yml` under `banks:`:
   ```yaml
   <bank>:
     closing_day: 15
     source_account: "<Bank Display Name>"
   ```

3. **Register in `src/generic_importer.py`**:
   ```python
   from import_<bank>_firefly import process_<bank>_statement
   BANK_PROCESSORS["<bank>"] = process_<bank>_statement
   ```

4. **Write tests** in `tests/test_<bank>.py` (TDD — write tests FIRST):
   - Happy path with sample data
   - Date parsing edge cases
   - Amount parsing edge cases
   - Invalid file handling

5. **Run tests**: `python -m pytest tests/test_<bank>.py -v`

6. **Validate**: `python src/generic_importer.py --bank <bank> --data sample.xlsx --dry-run`

Read `docs/context/importers.qmd` for full patterns and examples.
