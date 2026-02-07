# PDF Utils Improvements & Dummy Data Generator

This document describes the recent improvements to `pdf_utils.py` and the new dummy data generation script.

## 📈 Improvements to `pdf_utils.py`

### 1. **Enhanced Logging**
- Replaced `print()` statements with structured logging using `logging_config`
- Added debug, info, warning, and error level logging throughout
- Better error tracking and debugging capabilities

### 2. **Improved Error Handling**
- Added try-except blocks around critical operations
- Graceful degradation when optional libraries are missing
- Better error messages with context

### 3. **Enhanced Date Parsing**
The `parse_mx_date()` function now supports:
- ISO format: `2024-01-12` (already standardized)
- Spanish month abbreviations: `12 ENE`, `12ENE`
- Numeric formats: `12/01/24`, `12-01-2024`
- Full month names: `ENERO`, `FEBRERO`, etc.
- Better validation and error reporting

### 4. **Robust Amount Parsing**
- `parse_amount_str()` now returns `None` on failure instead of crashing
- Handles various formats: `1,234.56`, `1234.56`
- Proper error logging when parsing fails

### 5. **Better OCR Configuration**
- Configurable language parameter (`lang="spa+eng"`)
- Enhanced preprocessing with better error handling
- More detailed logging of OCR operations

### 6. **Improved Transaction Extraction**
- Better regex patterns for transaction rows
- Validates parsed amounts before adding to results
- More informative logging about extraction method and results
- Debug output for first page when no transactions found

### 7. **Enhanced Metadata Extraction**
- Smarter OCR fallback (only when critical data missing)
- Better region cropping for header extraction
- Validates parsed amounts before storing
- Comprehensive logging of extraction results

### 8. **Documentation**
- Added comprehensive docstrings to all functions
- Included examples in docstrings
- Better inline comments explaining logic

## 🎯 Dummy Data Generator

### Overview
The `generate_dummy_data.py` script creates realistic transaction data for testing the analytics dashboard without needing real bank statements.

### Features

#### **Realistic Merchant Data**
- 70+ real Mexican merchants across 9 categories:
  - 🛒 Groceries (OXXO, Walmart, Soriana, etc.)
  - 🍔 Restaurants (McDonald's, Starbucks, etc.)
  - 🚗 Transport (Uber, Pemex, etc.)
  - 🛍️ Shopping (Liverpool, Zara, etc.)
  - 🎬 Entertainment (Cinepolis, Netflix, etc.)
  - 📱 Subscriptions (Spotify, Amazon Prime, etc.)
  - 🏥 Health (Farmacias, hospitals, etc.)
  - 💳 Fees (Bank commissions, interest, etc.)
  - 🌐 Online (Mercado Libre, Amazon, etc.)

#### **Proper Categorization**
- Firefly III compatible expense accounts
- Merchant tags for smart matching
- Period tags for statement filtering
- Category names for analytics

#### **Realistic Amounts**
- Category-specific amount ranges
- Random variation within realistic bounds
- Groceries: $20-$500
- Restaurants: $50-$800
- Shopping: $100-$2,500
- etc.

#### **Multi-Period Support**
- Generates 6 months of historical data by default
- Proper period tagging (YYYY-MM format)
- Realistic transaction distribution across dates

### Usage

```bash
# Generate dummy data for both banks
python scripts/generate_dummy_data.py
```

This creates:
- `data/santander/firefly_likeu.csv` (360 transactions)
- `data/hsbc/firefly_hsbc.csv` (330 transactions)

### Output Example

```
✅ Created data/santander/firefly_likeu.csv
   - 360 transactions
   - Date range: 2025-08-17 to 2026-02-06
   - Total spent: $198,907.44
```

### CSV Structure

Generated CSVs are fully compatible with the Firefly III import format:

```csv
date,amount,description,type,source_name,source_id,destination_name,destination_id,currency_code,foreign_currency_code,foreign_amount,internal_reference,external_id,notes,category_name,tags
2025-08-17,391.94,LA COMER,withdrawal,Santander LikeU,santander_likeu_main,Expenses:Food:Groceries,,MXN,,,,,,Groceries,"merchant:la_comer,period:2025-09"
```

### Customization

You can modify the script to:
- Change number of months: `months_back=12`
- Adjust transactions per month: `txns_per_month=100`
- Add new merchants to `MERCHANTS` dict
- Modify amount ranges in `AMOUNT_RANGES`
- Change category mappings in `CATEGORY_ACCOUNTS`

## 🧪 Testing the Dashboard

After generating dummy data:

1. **Start the Streamlit app:**
   ```bash
   streamlit run src/app.py
   ```

2. **Navigate to Analytics tab**
   - View Santander and HSBC transaction analytics
   - Test period filtering
   - Test date range filtering
   - Explore category breakdowns
   - View monthly spending trends
   - Test merchant search and rule creation

3. **Test Features:**
   - ✅ Categorization coverage metrics
   - ✅ Category deep dive charts
   - ✅ Monthly spending trends
   - ✅ Transaction drilldown by category
   - ✅ Period-based filtering
   - ✅ Date range filtering
   - ✅ Merchant fuzzy search
   - ✅ ML prediction testing
   - ✅ Rule staging workflow

## 📊 Dashboard Features Now Testable

With dummy data, you can now test:

1. **Metrics Dashboard**
   - Total transactions
   - Total spent
   - Categorization coverage
   - Transaction type distribution

2. **Visual Analytics**
   - Categorization pie charts
   - Transaction type bar charts
   - Category spending breakdown
   - Monthly trends line charts

3. **Filters**
   - Period selector (2025-09, 2025-10, etc.)
   - Date range selector (custom start/end dates)
   - Category drilldown

4. **Rule Hub**
   - Merchant selection with fuzzy search
   - ML category predictions
   - Rule staging
   - Batch rule application

## 🔄 Regenerating Data

To regenerate fresh dummy data:

```bash
# Remove old data
rm -rf data/santander/firefly_likeu.csv data/hsbc/firefly_hsbc.csv

# Generate new data
python scripts/generate_dummy_data.py
```

## 📝 Notes

- Dummy data is **completely random** and not based on real transactions
- Merchants and amounts are realistic but fictional
- Use this data only for testing and development
- **Do not commit generated CSV files to git** (already in `.gitignore`)

## 🚀 Next Steps

1. Test all dashboard features with dummy data
2. Identify any UI/UX issues
3. Validate analytics calculations
4. Test rule creation workflow
5. Verify ML predictions work correctly
6. Test with real data when ready

---

**Created:** 2026-02-06
**Author:** Claude Code
**Version:** 1.0
