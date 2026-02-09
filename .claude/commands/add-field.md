# Add Transaction Field

Step-by-step guide to add a new field to the Transaction model: $ARGUMENTS

## 5-Step Workflow

### Step 1: Update Domain Model

Edit `src/domain/transaction.py`:

```python
@dataclass
class Transaction:
    # ... existing fields ...
    new_field: Optional[str] = None  # Add with default for backwards compat
```

### Step 2: Update Validation

Edit `src/validation.py` — add validator for the new field:

```python
def validate_new_field(value: Optional[str]) -> Optional[str]:
    """Validate new_field."""
    if value is not None and not isinstance(value, str):
        raise ValidationError(f"new_field must be str, got {type(value)}")
    return value
```

Register in the Transaction validator:
```python
Transaction(
    # ...
    new_field=validate_new_field(raw.get("new_field")),
)
```

### Step 3: Update Importers

For each bank importer in `src/import_*_firefly.py`, populate the new field:

```python
transaction = Transaction(
    # ...
    new_field=row.get("source_column"),
)
```

### Step 4: Update Analytics (if needed)

If the field affects reporting, edit `src/services/analytics_service.py`:

```python
# Add to aggregation queries or metrics calculations
```

### Step 5: Write Tests

```bash
# TDD first — create tests before implementation
touch tests/test_validation.py  # Add new_field tests here
pytest tests/test_validation.py -v
```

Add tests covering:
- Valid field values
- Invalid types (should raise ValidationError)
- None/empty handling
- Boundary values

## Quick Reference

| File | What to Change |
|------|---------------|
| `src/domain/transaction.py` | Add field to dataclass |
| `src/validation.py` | Add validator function |
| `src/import_*_firefly.py` | Populate from source data |
| `src/services/analytics_service.py` | Include in queries (if needed) |
| `tests/test_validation.py` | Add field validation tests |

Read `docs/context/domain.qmd` for full domain model context.
