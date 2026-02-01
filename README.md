# ledger-smart-converter

A collection of tools to import bank account and credit card statements (HSBC Mexico, Santander LikeU) into [Firefly III](https://www.firefly-iii.org/).

It features an intelligent **Learning Cycle** that helps you progressively categorize transactions using regex rules and assisted learning.

## Features

-   **Santander LikeU**: Import from XLSX statements + PDF (for summary validation).
-   **HSBC Mexico**: Import from CFDI (XML) statements.
-   **Analytics Dashboard**: Visualize spending metrics, category breakdowns, and bank comparisons.
-   **Interactive Rule Correction**: Fix miscategorizations directly from the web app and update rules instantly.
-   **Statement Cycle Logic**: Automatic tagging of transactions with their statement period (`period:YYYY-MM`).
-   **Rule-based Categorization**: Regex rules compatible with standard Firefly III concepts.
-   **PDF Data Extraction (with OCR)**: Extracts Cutoff and Payment dates, with a Tesseract OCR fallback for scanned documents.

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
    Run the setup script to create a virtual environment and install dependencies.
    ```powershell
    .\scripts\setup_env.ps1
    ```

## Usage

### 1. Web Interface & Analytics (Recommended)
The web interface provides the most feature-rich experience.

```powershell
.\scripts\run_web.ps1
```
This will open a browser at `http://localhost:8501` where you can:
-   **Import**: Upload XML/XLSX/PDF files and download Firefly-ready CSVs.
-   **Analyze**: View Total Spent, Categorization Coverage, and Category Spending charts.
-   **Drill-down**: Use the category filters to see exactly which transactions are in a category.
-   **Fix**: Use the **Rule Correction Hub** to fix a transaction and update `rules.yml` on the fly.

### 2. Manual & Learning Cycle
You can still run imports manually or use the automated learning cycle.

**Manual Import**:
```powershell
.\scripts\run_hsbc_example.ps1
.\scripts\run_full_example.ps1
```

**Learning Cycle**:
```powershell
.\scripts\run_learning_cycle.ps1 -Bank hsbc
```
*Processes data, suggests new rules, merges them into a temporary file for your review.*

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
