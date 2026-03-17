---
name: categorization-rules
description: Use this skill for managing categorization rules, validating configuration, and retraining the ML model.
---

# Categorization & Rules Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/ml-categorization.qmd` before modifying rules or the ML classifier.
2. **Precision Navigation**: Use `codegraph_node "MLCategorizer"` to understand the classification pipeline.

## Workflow: Add Categorization Rule (SAFE)

**NEVER edit `config/rules.yml` directly.**

1. **Stage rule change**: Add to `config/rules.pending.yml` or use `src/services/rule_service.py:stage_rule_change()`.
2. **Merge pending rules**: Use `src/services/rule_service.py:merge_pending_rules()`.
   - This creates a backup in `config/backups/`.
   - The ML model retrains automatically after a successful merge.

## ML Model Retraining

To manually trigger retraining:
```bash
python -c "from src.ml_categorizer import MLCategorizer; MLCategorizer().train_global_model()"
```

## Config Validation

Validate `config/rules.yml` syntax and structure:
```bash
python src/healthcheck.py
```

## Related Agents
- **ML/Rules Agent**: Manages classification pipeline and rule integrity.

## Normalized Description Feature

The ML model uses `normalized_description` as its primary text feature (preferred over raw `description`).

**Text column priority**:
1. `normalized_description` — deterministic normalized text from `description_normalizer.py`
2. `description` — raw legacy field (fallback for older rows)

**Backfill**: If rows are missing `normalized_description`, run before retraining:
```python
from services.db_service import DatabaseService
from description_normalizer import normalize_description

db = DatabaseService()
db.initialize()
db.backfill_normalized_descriptions(normalize_description)
```

This ensures the ML model trains on normalized text, improving categorization consistency.
