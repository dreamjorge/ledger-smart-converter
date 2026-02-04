# ledger-smart-converter

A collection of tools to import bank account and credit card statements (HSBC Mexico, Santander LikeU) into [Firefly III](https://www.firefly-iii.org/).

It features an intelligent **Learning Cycle** that helps you progressively categorize transactions using regex rules and assisted learning.

## Features

-   **Santander LikeU**: Import from XLSX statements or directly from PDF using OCR.
-   **HSBC Mexico**: Import from CFDI (XML) statements or PDF (OCR).
-   **Analytics Dashboard**: Visualize spending metrics, category breakdowns, and bank comparisons.
-   **🧠 AI Smart Suggestions**: Integrated ML predictions suggest categories based on your history.
-   **🛠️ Rule Correction Hub**: Fix miscategorizations and "teach" the AI with one click.
-   **🔍 Fuzzy Merchant Search**: Find merchants effortlessly, even with typos or varying descriptions.
-   **Statement Cycle Logic**: Automatic tagging of transactions with their statement period (`period:YYYY-MM`).
-   **🌎 Bilingual Support**: Full Spanish/English support across the entire interface.
-   **PDF Data Extraction (with OCR)**: Tesseract fallback for scanned documents.

## Folder Structure

-   `src/`: Python source code (importers, utilities).
-   `config/`: Configuration files (`rules.yml`).
-   `scripts/`: PowerShell scripts for execution.
-   `data/`: Persistent storage for each bank (input files and generated CSVs).
    -   `hsbc/`: `firefly_hsbc.csv`, `unknown_merchants.csv`.
    -   `santander/`: `firefly_likeu.csv`, `unknown_merchants.csv`.

## Installation

1.  **Prerequisites**:
    -   Python 3.8+
    -   PowerShell (Windows)
    -   [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Optional: for scanned PDF support)

2.  **Setup**:
    Run the setup script to create the environment and install dependencies (including `scikit-learn` and `rapidfuzz` for AI features).
    ```powershell
    .\scripts\setup_env.ps1
    ```

## Usage

### 1. Launch the App
Start the web interface using the dedicated script:
```powershell
.\scripts\run_web.ps1
```
Open your browser at `http://localhost:8501`.

### 2. Importing Statements
Go to the **"Import Files"** tab:
- **Standard**: Upload your XML (HSBC) or XLSX (Santander) along with the PDF.
- **OCR (No Data File)**: If you only have a PDF scan, upload it and check the box **"🔍 Use PDF as primary data source (OCR)"**.
- Click **Process Files** to generate a Firefly-ready CSV.

### 3. Analytics & Exploration
Switch to the **"Analytics Dashboard"** tab to:
- See **Total Spent** per bank and per period.
- Explore **Category Deep Dives** with distribution charts.
- Use the **Transaction Drill-down** to find specific expenses by category.

### 4. Smart Rule Correction (AI-Powered)
Found a miscategorized transaction? Scroll to the bottom of the Dashboard:
1. **Fuzzy Search**: Use the search box to find the merchant (e.g., "WAL" will find "WALMART CASHI").
2. **AI Prediction**: The system will show: `🤖 ML Prediction: Suggested category is Groceries (95%)`.
3. **Verify & Save**: The category is pre-filled for you. Just click **Save Rule & Regenerate**.
4. **Instant Retraining**: The AI learns from your correction immediately for future statements!

---

## Security & Privacy
- **100% Local**: All processing, OCR, and Machine Learning happen on your machine.
- **Privacy First**: No data is sent to the cloud. Your `data/` folder and sensitive files are protected by `.gitignore`.

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
