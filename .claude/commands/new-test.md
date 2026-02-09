# Create New Test

Create a new test file following TDD workflow for: $ARGUMENTS

## Mandatory TDD Workflow

1. **Create test file FIRST** (before writing feature code):
   ```bash
   touch tests/test_<module>.py
   ```

2. **Write failing tests** (red phase):
   ```python
   # tests/test_<module>.py
   import pytest
   from src.<module> import function_to_test

   class TestFunctionName:
       """Test suite for function_to_test."""

       def test_happy_path(self):
           result = function_to_test("valid_input")
           assert result == "expected"

       def test_error_handling(self):
           with pytest.raises(ValueError):
               function_to_test("invalid_input")

       def test_edge_cases(self):
           assert function_to_test("") is None
           assert function_to_test(None) is None
   ```

3. **Run to confirm they fail**: `pytest tests/test_<module>.py -v`

4. **Implement feature** until tests pass (green phase)

5. **Coverage targets**:
   - New modules: 85%+
   - Critical paths (imports, validation, ML): 90%+
   - Utilities: 100%

## Test Patterns

- **Fixtures**: Use `tmp_path` for temp files, define `@pytest.fixture` for shared data
- **Parametrize**: Use `@pytest.mark.parametrize` for multiple input cases
- **Mocking**: Use `unittest.mock.patch` for external dependencies
- **Naming**: `test_<function>_<scenario>` — e.g., `test_parse_date_handles_spanish_months`

Read `docs/context/testing.qmd` for full patterns, fixtures, and CI details.
