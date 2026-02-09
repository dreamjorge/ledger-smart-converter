# Retrain ML Categorization Model

Retrain the ML categorization model with current rules. $ARGUMENTS

## Trigger Retraining

```python
# From Python (in project root)
from src.ml_categorizer import MLCategorizer

ml = MLCategorizer()
ml.train_global_model()
```

```bash
# Or run directly
python -c "from src.ml_categorizer import MLCategorizer; MLCategorizer().train_global_model()"
```

## When to Retrain

- After adding/modifying categorization rules in `config/rules.yml`
- After running `/add-rule` to merge pending rules
- When ML prediction accuracy has degraded
- After importing a large batch of manually categorized transactions

## What Happens

1. Loads all categorized transactions from `data/*/output/*.csv`
2. Extracts features (merchant name, amount, description)
3. Trains sklearn classifier on labeled data
4. Saves model artifact for future predictions

## Debugging

- Check training data quality: ensure transactions have categories
- Review rules in `config/rules.yml` for conflicts
- See `src/ml_categorizer.py` for model implementation
- Read `docs/context/ml-categorization.qmd` for full ML context
