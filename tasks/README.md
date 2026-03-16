# Tasks

Enhancement backlog identified from project analysis (2026-03-16).
Each file is a self-contained task with context, specific changes, and acceptance criteria.

## Index

| # | Task | Area | Priority | Effort |
|---|------|------|----------|--------|
| [01](01-claude-md-enhancements.md) | Update CLAUDE.md | Documentation | Medium | 30 min |
| [02](02-agents-md-enhancements.md) | Update AGENTS.md | Documentation / Agents | High | 1–2 h |
| [03](03-new-db-qmd-context.md) | Create `docs/context/db.qmd` | Context / Documentation | High | 1–2 h |
| [04](04-update-existing-qmd-files.md) | Update existing QMD files | Context / Documentation | High | 2–3 h |
| [05](05-new-db-operations-skill.md) | Create `skills/db-operations/SKILL.md` | Skills | Medium | 30 min |
| [06](06-update-existing-skills.md) | Update 3 existing skills | Skills | Medium | 45 min |
| [07](07-ci-improvements.md) | CI/CD improvements | DevOps | High | 30 min |
| [08](08-test-performance.md) | Investigate test suite runtime (39 min) | Testing | Medium | 2–4 h |
| [09](09-code-enhancements.md) | Code-level enhancements (6 items) | Code | Low–Medium | Varies |

## Suggested Order

```
High priority (do first):
  07 → CI threshold + slow test split    (small, high impact)
  03 → New db.qmd                        (fills biggest context gap)
  04 → Update existing QMDs              (keeps context current)
  02 → Update AGENTS.md                  (routing is stale)

Medium priority:
  01 → Update CLAUDE.md                  (agent first-read context)
  05 → New db-operations skill           (needed alongside db.qmd)
  06 → Update existing skills            (small additions)
  08 → Test performance investigation    (identify root cause first)

Low priority:
  09 → Code enhancements                 (item by item, not a single PR)
```

## Key Findings

- **Biggest context gap**: No `docs/context/db.qmd` — DB layer fully undocumented for agents
- **Stale routing**: AGENTS.md references no DB agent, no db.qmd, no DB slash command
- **CI inconsistency**: CI enforces 60% coverage but project policy states 85%
- **Test performance**: 39-min non-slow suite suggests heavy imports in test collection
- **Flet status unknown**: Prototype exists in src/ but is undocumented in CLAUDE.md/AGENTS.md
