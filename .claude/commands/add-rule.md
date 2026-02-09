# Add Categorization Rule

Stage a new categorization rule for: $ARGUMENTS

Use the **safe rule workflow** (never edit `config/rules.yml` directly):

1. **Via UI** (preferred): Use the Rule Hub in the Analytics tab
   - Search merchant → review ML suggestion → select category → stage rule

2. **Via code** (`src/services/rule_service.py`):
   ```python
   from services.rule_service import stage_rule_change
   from pathlib import Path

   ok, result = stage_rule_change(
       rules_path=Path("config/rules.yml"),
       pending_path=Path("config/rules.pending.yml"),
       merchant_name="MERCHANT NAME",
       regex_pattern="MERCHANT.*",
       expense_account="Expenses:Category:Subcategory",
       bucket_tag="category_tag"
   )
   ```

3. **Category hierarchy format**: `Expenses:Parent:Child`
   - Common: `Expenses:Food:Groceries`, `Expenses:Transport:Uber`
   - Available tags: groceries, restaurants, transport, shopping, subscriptions, entertainment, health, fees, online

4. **Merge when ready**:
   ```python
   from services.rule_service import merge_pending_rules
   ok, result = merge_pending_rules(
       rules_path, pending_path, backup_dir=Path("config/backups")
   )
   # Backup auto-created in config/backups/rules_YYYYMMDD_HHMMSS.yml
   # ML model retrains automatically
   ```

Read `docs/context/ml-categorization.qmd` for the full workflow and conflict resolution.
