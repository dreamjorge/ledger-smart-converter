---
name: ledger-smart-converter
description: Main skill for the Ledger Smart Converter project. Coordinates bank importers, categorization, analytics, and testing. Enforces QMD context and CodeGraph usage for token efficiency.
---

# Ledger Smart Converter Skill

## 🚀 Core Mandate: Token Efficiency

To minimize token usage and maximize precision, all assistant actions **MUST**:
1. **Read QMD Context First**: Always read the relevant file in `docs/context/` before requesting broad file contents.
2. **Use CodeGraph for Navigation**: Use `codegraph_*` tools instead of full-file reads or broad grep/glob patterns.

## 🛠️ Specialized Project Skills

This project leverages specialized skills for distinct task areas. Refer to these for detailed workflows:

- **[Bank Importer](file:///d:/Repositories/credit_cards/skills/bank-importer/SKILL.md)**: Add/fix bank parsers and ingestion logic.
- **[Testing & TDD](file:///d:/Repositories/credit_cards/skills/testing/SKILL.md)**: Run tests, enforce 85% coverage, and follow TDD.
- **[Categorization & Rules](file:///d:/Repositories/credit_cards/skills/categorization/SKILL.md)**: Manage rules, retrain ML, and validate config.
- **[Domain & Validation](file:///d:/Repositories/credit_cards/skills/domain-model/SKILL.md)**: Modify transaction models and validation constraints.
- **[OCR & PDF Debug](file:///d:/Repositories/credit_cards/skills/ocr-debug/SKILL.md)**: Debug PDF extraction and Tesseract fallback.
- **[Analytics & Dashboard](file:///d:/Repositories/credit_cards/skills/analytics/SKILL.md)**: Update metrics, queries, and Streamlit UI.
- **[Diagnostics](file:///d:/Repositories/credit_cards/skills/diagnostics/SKILL.md)**: Run health checks and validate environment.

## 🎯 Definition of Done

- Behavior implemented with tests.
- Relevant tests pass.
- Coverage gate passes at `>=85%`.
- Changes align with layer boundaries (domain/services/ui).
- **QMD and CodeGraph were used to reduce context overhead.**
