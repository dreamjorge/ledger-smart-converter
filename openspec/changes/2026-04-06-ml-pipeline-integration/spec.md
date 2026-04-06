# Spec: ML Pipeline Integration

## Domain: Categorization (ML Fallback)

### Requirement: ML MUST be applied only when rules fail

The system MUST attempt ML categorization ONLY when the rules engine returns the `fallback_expense`. If a rule matches, ML MUST NOT be called.

#### Scenario: Rule matches — ML skipped

- GIVEN a transaction description that matches a rule
- WHEN `process_transactions()` runs
- THEN `expense` is set by the rule
- AND `ml_categorizer.predict()` MUST NOT be called

#### Scenario: No rule match, ML high confidence — ML wins

- GIVEN a transaction that falls through to `fallback_expense`
- AND `ml_categorizer.is_trained == True`
- AND `ml_categorizer.predict()` returns confidence ≥ threshold (0.5)
- WHEN `process_transactions()` runs
- THEN `expense` is the ML prediction
- AND tag `ml:predicted` is added to the transaction

#### Scenario: No rule match, ML low confidence — stays uncategorized

- GIVEN a transaction that falls through to `fallback_expense`
- AND ML returns confidence < threshold
- WHEN `process_transactions()` runs
- THEN `expense` remains `fallback_expense`
- AND `ml:predicted` tag MUST NOT be added

#### Scenario: No ML categorizer provided — legacy behavior

- GIVEN `ml_categorizer=None`
- WHEN `process_transactions()` runs
- THEN behavior is identical to pre-ML: expense = fallback_expense for unmatched txns
- AND no errors are raised

#### Scenario: ML categorizer not trained — ML skipped

- GIVEN `ml_categorizer.is_trained == False`
- WHEN `process_transactions()` runs
- THEN ML is not called
- AND expense remains from rules engine output

## Success Criteria

- [ ] `test_ml_fallback_high_confidence` — ML prediction used when confidence ≥ 0.5
- [ ] `test_ml_fallback_low_confidence` — stays uncategorized when confidence < 0.5
- [ ] `test_ml_skipped_on_rule_match` — ML not called when rule matches
- [ ] `test_no_ml_categorizer` — None categorizer → no error, fallback behavior
- [ ] `test_ml_not_trained` — untrained categorizer → ML skipped
