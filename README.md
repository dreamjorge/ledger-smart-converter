# ledger-smart-converter

# ledger-smart-converter

A collection of tools to import bank account and credit card statements (HSBC Mexico, Santander LikeU) into [Firefly III](https://www.firefly-iii.org/).

It features an intelligent **Learning Cycle** that helps you progressively categorize transactions using regex rules and assisted learning.

## Features

-   **Desktop App (Flet)**: New native-inspired desktop interface for a smoother experience.
-   **Santander LikeU**: Import from XLSX statements or directly from PDF using OCR.
-   **HSBC Mexico**: Import from CFDI (XML) statements or PDF (OCR).
-   **Analytics Dashboard**: Visualize spending metrics, category breakdowns, and bank comparisons.
-   **👥 Family Profiles**: PIN-protected multi-user support for managing shared/individual accounts.
-   **📝 Manual Entry**: Add individual transactions directly from the UI.
-   **🧹 Smart Deduplication**: Interactive resolution of duplicates during batch imports (Skip/Overwrite/Keep Both).
-   **🧠 AI Smart Suggestions**: Integrated ML predictions suggest categories based on your history.
-   **🛠️ Rule Correction Hub**: Fix miscategorizations and "teach" the AI with one click.
-   **🔍 Fuzzy Merchant Search**: Find merchants effortlessly, even with typos or varying descriptions.
-   **Statement Cycle Logic**: Automatic tagging of transactions with their statement period (`period:YYYY-MM`).
-   **🌎 Bilingual Support**: Full Spanish/English support across the entire interface.
-   **PDF Data Extraction (with OCR)**: Tesseract fallback for scanned documents.
-   **✅ Reliability & Validation Layer**: Canonical transaction model, strict validation, structured importer logging, and deterministic processing.
-   **✅ Safe Rules Workflow**: Stage changes in `config/rules.pending.yml`, detect conflicts, and merge with automatic backups.
-   **✅ CI Ready**: Automated compile + test checks via GitHub Actions (`.github/workflows/ci.yml`).

## Folder Structure

-   `src/`: Python source code (importers, utilities).
-   `src/services/`: Service orchestration layer (import, analytics, rules, users, manual entry, dedup).
-   `src/ui/pages/`: Streamlit page modules (import + analytics + settings).
-   `src/ui/flet_ui/`: Flet desktop view components and layout.
-   `config/`: Configuration files (`rules.yml`, `accounts.yml`).
-   `scripts/`: Automation and execution scripts.
-   `.github/workflows/`: CI pipelines (test automation on push/PR).
-   `data/`: SQLite database (`ledger.db`) and bank-specific data.

## Deployment (Local / Server)

This project runs as a Streamlit app. You can deploy it locally or on a small VM.

### Option A: Web App (Streamlit)
Ideal for server deployment or browser-based access.

**Windows (PowerShell)**: `.\scripts\run_web.ps1`
**Linux/macOS**: `./scripts/run_web.sh`

### Option B: Desktop App (Flet)
Recommended for local desktop usage with native feel and navigation.

**Windows (PowerShell)**: `.\scripts\run_flet.ps1`
**Linux/macOS**: `./scripts/run_flet.sh`

---

### Setup Instructions
All interfaces share the same environment:

**Windows (PowerShell)**: `.\scripts\setup_env.ps1`
**Linux/macOS**: `./scripts/setup_env.sh`

`setup_env` now expects [`uv`](https://docs.astral.sh/uv/) on your `PATH`, creates a repo-local `.venv` with `uv venv`, and installs `requirements.txt` into that environment with `uv pip install -r`.

## Statement Cycles & Tagging

Each transaction is automatically tagged with:
-   `card:likeu` or `card:hsbc`
-   `period:YYYY-MM` (Calculated based on the `closing_day` in `rules.yml`)

You can select specific periods in the Analytics Dashboard to view monthly spending trends.

## PDF Verification & OCR
When you upload a PDF statement:
1.  **Text Extraction**: The tool reads summary info (dates/amounts) directly.
2.  **OCR Fallback**: If text reading fails (e.g., scanned PDF), it uses **Tesseract OCR** to extract the information.
    - *Default Windows path checked*: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### Feedback loop
Use `src/pdf_feedback.py` when you want to compare the OCR output against the XML reference and collect the rows that still fail.
```powershell
.\.venv\Scripts\python.exe src\pdf_feedback.py `
  --pdf data\hsbc\statements.pdf `
  --xml data\hsbc\statements.xml
```
The script writes `data/hsbc/feedback/feedback_summary.json`, `pdf_only.csv`, `xml_only.csv`, and `raw_lines.csv` so you can tune `src/pdf_utils.py` (regex, date parsing, preprocessing) based on real mismatches before dropping the XML altogether.

## Configuration (`rules.yml`)

Configure account names and closing dates at the top:

```yaml
defaults:
  accounts:
    credit_card:
      name: Liabilities:CC:Santander LikeU
      closing_day: 15
    hsbc_credit_card:
      name: Liabilities:CC:HSBC
      closing_day: 20
```

And define your categorization rules below:

```yaml
rules:
  - name: "Groceries"
    any_regex: ["WALMART", "OXXO", "SORIANA"]
    set:
      expense: "Expenses:Food:Groceries"
      tags: ["bucket:groceries"]
```
