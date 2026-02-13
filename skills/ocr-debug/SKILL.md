---
name: ocr-debugging
description: Use this skill for debugging PDF transaction extraction, fixing regex patterns, and optimizing OCR (Tesseract) fallback.
---

# OCR Debug Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/importers.qmd` (PDF Utilities section) before modifying parsing logic.
2. **Precision Navigation**: Use `codegraph_callers "extract_transactions_from_pdf"` to map existing ingestion paths.

## Diagnostic Workflow

1. **Run feedback tool** to compare OCR vs reference:
   ```bash
   python src/pdf_feedback.py --pdf statement.pdf --xml statement.xml
   ```
2. **Review feedback output** in `data/<bank>/feedback/`.
3. **Verify regex patterns** in `src/pdf_utils.py`:
   - Check `PATTERNS["cutoff_date"]` and `PATTERNS["period"]`.
   - Ensure amount patterns handle locale-specific formatting (e.g., Mexican thousands separator).
4. **Test date/amount parsing hooks**:
   - `parse_mx_date()`
   - `parse_amount_str()`

## Enabling OCR
- Requires Tesseract installed on the system.
- Set `use_ocr=True` in parsing calls when text extraction fails.

## Related Agents
- **OCR Agent**: Specialist in PDF/Image extraction.
