---
name: bank-importer
description: Use this skill for adding new bank importers, modifying existing parsers, or debugging bank-specific statement ingestion.
---

# Bank Importer Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/importers.qmd` before analyzing code.
2. **Precision Navigation**: Use `codegraph_search "import_.*_firefly"` and `codegraph_impact` to understand the ingestion flow without full file reads.

## Workflow: Add New Bank Importer

1. **Create importer file** `src/import_<bank>_firefly.py`:
   - Import `CanonicalTransaction` from `src.domain.transaction`.
   - Implement `process_<bank>_statement(file_path: Path) -> List[Dict]`.
   - Use `parse_mx_date()` from `src.pdf_utils` for date parsing.
   - Use `parse_amount_str()` for amount normalization.
   - Use `determine_statement_period()` from `src.common_utils` for period tagging.
   - Add structured logging via `from src.logging_config import get_logger`.

2. **Add config section** in `config/rules.yml` under `banks:`:
   ```yaml
   <bank>:
     closing_day: 15
     source_account: "<Bank Display Name>"
   ```

3. **Register in `src/generic_importer.py`**:
   - Register the new processor in the `BANK_PROCESSORS` mapping.

4. **TDD - Write tests FIRST** in `tests/test_<bank>.py`:
   - Test happy path with sample data.
   - Test date parsing edge cases.
   - Test amount parsing edge cases.
   - Test invalid file handling.

5. **Verify**:
   - Run tests: `python -m pytest tests/test_<bank>.py -v`
   - Dry run: `python src/generic_importer.py --bank <bank> --data sample.xlsx --dry-run`

## Related Agents
- **Import Agent**: Responsible for new/fixing bank parsers.
- **OCR Agent**: For PDF extraction issues (use `fix-ocr` logic).
