---
name: project-testing
description: Use this skill for test-driven development (TDD), running pytest suites, and enforcing code coverage (85% minimum).
---

# Testing Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/testing.qmd` before adding or modifying tests.
2. **Precision Navigation**: Use `codegraph_search "test_.*"` to find relevant test files and `codegraph_callers` to identify units under test.

## Workflow: TDD (Test-Driven Development)

1. **Create test file first**: `tests/test_<module>.py`.
2. **Write failing tests** for the expected behavior.
3. **Run tests to see them fail**: `python -m pytest tests/test_<module>.py`.
4. **Implement minimal code** to make tests pass.
5. **Refactor** and verify tests remain green.

## Test Commands

- **Quick run**: `python -m pytest tests/ -q`
- **Verbose run**: `python -m pytest tests/ -v`
- **Coverage enforcement**: `python -m pytest tests/ --cov=src --cov-fail-under=85`

## Coverage Requirements
- **New code**: 85%+ mandatory.
- **Critical paths**: 90%+ recommended.
- **Utilities**: 100% recommended.

## Related Agents
- **Testing Agent**: Manages test suites and CI validation.
