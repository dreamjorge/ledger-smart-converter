# Fix OCR / PDF Parsing

Debug and fix PDF parsing issues for: $ARGUMENTS

## Diagnostic Steps

1. **Run feedback tool** to compare OCR vs reference:
   ```bash
   python src/pdf_feedback.py --pdf statement.pdf --xml statement.xml
   ```

2. **Review feedback output** in `data/<bank>/feedback/` — shows:
   - Parsed vs expected values
   - Missed transactions
   - Date/amount mismatches

3. **Check regex patterns** in `src/pdf_utils.py`:
   - Date patterns: `PATTERNS["cutoff_date"]`, `PATTERNS["period"]`
   - Amount patterns: Mexican formatting (`1,234.56`)
   - Date parsing: `parse_mx_date()` supports `"12 ENE"`, `"12/01/24"`, ISO

4. **Test specific parsing**:
   ```python
   from pdf_utils import parse_mx_date, parse_amount_str, extract_transactions_from_pdf

   # Test date
   print(parse_mx_date("12 ENE", year=2024))  # "2024-01-12"

   # Test amount
   print(parse_amount_str("1,234.56"))  # 1234.56

   # Full extraction
   txns = extract_transactions_from_pdf(Path("statement.pdf"), use_ocr=True)
   ```

5. **Enable OCR** if text extraction fails:
   - Requires Tesseract: `apt install tesseract-ocr`
   - Set `use_ocr=True` in extraction call

Read `docs/context/importers.qmd` (PDF Utilities section) for patterns and examples.
