# Health Check

Run system health diagnostics for the Ledger Smart Converter.

```bash
python src/healthcheck.py
```

This validates:
- Python dependencies (sklearn, streamlit, pandas, pdfplumber, etc.)
- Tesseract OCR availability (optional, needed for scanned PDFs)
- Configuration files (`config/rules.yml`, `.env`)
- Data directories structure
- ML model training capability

If healthcheck fails:
1. Check `.env` file exists (copy from `.env.example`)
2. Run `pip install -r requirements.txt` to fix missing deps
3. Install Tesseract if OCR is needed: `apt install tesseract-ocr`
4. Verify `config/rules.yml` is valid YAML

Additional diagnostics:
```bash
# Dry-run import to test pipeline
python src/generic_importer.py --bank santander_likeu --data sample.xlsx --dry-run

# Generate test data for dashboard
python scripts/generate_dummy_data.py

# Start web UI
streamlit run src/web_app.py
```
