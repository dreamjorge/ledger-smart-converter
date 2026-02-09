# Generate Dummy Test Data

Generate realistic test transaction data for the dashboard. $ARGUMENTS

## Run Generator

```bash
python scripts/generate_dummy_data.py
```

## What It Creates

- **690 transactions** across multiple months
- **70+ Mexican merchants** (OXXO, Liverpool, Costco, etc.)
- **9 categories** (Food, Transport, Shopping, etc.)
- Realistic amounts and date distributions
- Output: `data/dummy/output/transactions.csv`

## Use Cases

- Test the analytics dashboard with realistic data
- Validate ML categorization without real bank data
- Demo the UI to stakeholders
- Reproduce edge cases for debugging

## Options

```bash
# Default (690 transactions)
python scripts/generate_dummy_data.py

# Custom count (if supported)
python scripts/generate_dummy_data.py --count 1000

# Specific date range
python scripts/generate_dummy_data.py --months 6
```

## After Generating

1. Start the web UI: `streamlit run src/web_app.py`
2. Navigate to Analytics dashboard
3. Data will appear automatically (reads from `data/` directory)

See `AGENTS.md` for full testing infrastructure notes.
