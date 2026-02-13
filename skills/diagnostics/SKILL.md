---
name: project-diagnostics
description: Use this skill for running system health checks, validating environment dependencies, and diagnosing configuration issues.
---

# Diagnostics Skill

## Mandates for Token Efficiency

1. **Health First**: Always run the automated healthcheck before deep manual diagnostics.

## Diagnostic Commands

- **Full Healthcheck**:
  ```bash
  python src/healthcheck.py
  ```
  - Validates `config/rules.yml` syntax.
  - Checks for missing dependencies.
  - Verifies data directory accessibility.

- **Config Integrity**:
  ```bash
  python -c "import yaml; from pathlib import Path; yaml.safe_load(Path('config/rules.yml').read_text())"
  ```

## Common Resolutions
- Missing Tesseract: Install `tesseract-ocr`.
- Missing Categories: Check `categories:` list in `config/rules.yml`.
- Rule Conflicts: Check staged changes in `config/rules.pending.yml`.
