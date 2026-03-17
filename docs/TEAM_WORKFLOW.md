# Multi-Agent Team Workflow: Gemini, Claude & Codex

This document outlines the collaborative strategy for using three distinct AI agents to maximize engineering quality while optimizing token consumption.

## 🤖 Agent Roles & Strengths

| Agent | Primary Persona | Token Strength | Best Used For |
| :--- | :--- | :--- | :--- |
| **Gemini CLI** | **The Architect / Researcher** | **Massive Context (2M+ tokens)**. Can ingest the entire repository and all QMD context files in a single pass. | Broad codebase analysis, cross-module dependency mapping, long-term planning, and generating master strategies. |
| **Claude CLI** | **The Senior Engineer** | **High Coding Logic & Precision**. Superior at iterative TDD and complex implementation details. | Focused implementation of specific modules, writing complex business logic, and surgical bug fixing. |
| **Codex CLI** | **The Shell Assistant** | **Atomic Execution & Speed**. Best for one-shot shell translations and repetitive boilerplate. | Generating mock data, running quick shell commands (`codex exec`), code reviews (`codex review`), and boilerplate generation. |

---

## 🔄 The 3-Phase Lifecycle

### Phase 1: Research & Strategy (Gemini CLI)
*   **Goal**: Create a detailed, context-aware implementation plan.
*   **Workflow**:
    1.  Ingest all relevant `docs/context/*.qmd` files.
    2.  Use `codebase_investigator` to map the "blast radius" of the requested change.
    3.  Generate a `PLAN.md` with step-by-step instructions and test cases.
*   **Token Saving**: Gemini reads the "big picture" so other agents don't have to.

### Phase 2: Execution & Implementation (Claude CLI)
*   **Goal**: High-fidelity code implementation with TDD.
*   **Workflow**:
    1.  Provide Claude with the `PLAN.md` from Phase 1.
    2.  Use Claude's interactive loop to write tests first, then implementation.
    3.  Iterate until all tests pass and coverage requirements are met.
*   **Token Saving**: Claude stays focused on small, high-value file sets.

### Phase 3: Validation & Boilerplate (Codex CLI)
*   **Goal**: auxiliary tasks and final verification.
*   **Workflow**:
    1.  Use `codex review` to audit the changes made by Claude.
    2.  Use `codex exec "generate 100 sample transactions for HSBC"` to create test fixtures.
    3.  Use `codex apply` for quick git operations or patch applications.
*   **Token Saving**: Prevents "brain drain" on Gemini/Claude for low-complexity tasks.

---

## 🎫 Token Balancing Strategy

1.  **Single-Pass Reading**: Use Gemini for anything that requires reading more than 5 files at once.
2.  **Context Handoff**: Never make Claude "re-discover" what Gemini already found. Pass specific file paths and symbol names in the handoff.
3.  **Atomic Writing**: Use Codex for small standalone scripts or one-liners to keep the main agent's history clean.
4.  **Checkpointing**: Use `docs/checkpoint-*.md` to sync state between agents. If Claude runs out of tokens, Gemini reads the checkpoint and generates a new plan for a fresh Claude session.

## 🛠️ Integrated Commands Example

```bash
# 1. Gemini: Research and Plan
gemini "Analyze how to add HSBC PDF support and create a PLAN.md in /docs"

# 2. Claude: Implement following the plan
claude "Implement the HSBC parser as described in docs/PLAN.md. Run tests/test_hsbc.py until green."

# 3. Codex: Generate Data & Review
codex exec "Create a sample HSBC PDF layout in tests/fixtures/hsbc_sample.txt"
codex review src/import_hsbc_firefly.py
```
