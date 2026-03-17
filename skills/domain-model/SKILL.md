---
name: domain-models
description: Use this skill for modifying the Transaction domain model, updating field validators, and managing canonical data structures.
---

# Domain Model & Validation Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/domain.qmd` before changing data models.
2. **Precision Navigation**: Use `codegraph_impact "Transaction"` to assess the blast radius of a model change.

## Workflow: Add/Modify Transaction Field

1. **Update Domain Model**: Edit `src/domain/transaction.py`.
2. **Update Validators**: Edit `src/validation.py` to ensure the new field is properly constrained.
3. **Update Importers**: Ensure all relevant parsers in `src/import_*_firefly.py` populate the new field.
4. **Update Analytics**: If applicable, update `src/services/analytics_service.py` to use the new field.
5. **Verify**: Run `pytest tests/test_validation.py`.

## Related Agents
- **Validation Agent**: Guardian of data integrity and domain contracts.
