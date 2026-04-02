# Proposal: Fix Flet Pre-Merge Regressions

## Intent
Stabilize `feat/flet-migration-foundation` before merge by fixing six verified regressions that break deduplication safety, global analytics, and Flet Rule Hub behavior.

## Scope

### In Scope
- Make `source_hash` and duplicate checks account-aware so identical transactions from different accounts do not collide.
- Detect duplicates already present in the same import batch, not only rows already stored in SQLite.
- Restore global analytics reads by handling the all-accounts path without passing `bank_id=None` into bank-scoped loaders.
- Align manual entry and Flet Rule Hub category sources with canonical rule data and actual retraining behavior.

### Out of Scope
- New importer features, schema redesigns, or Firefly export changes.
- Broader Flet UI polish unrelated to these verified defects.

## Approach
Normalize dedup identity around canonical account context, then apply the same identity consistently in `DatabaseService`, batch dedup, and manual entry. Split analytics loading into bank-scoped and global-safe paths. Reuse canonical rule parsing for manual entry/Flet category options, trigger ML retraining only when merge succeeds, and remove hardcoded non-canonical category values from the Flet Rule Hub.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/services/db_service.py` | Modified | Rebuild source-hash inputs and duplicate existence checks. |
| `src/services/dedup_service.py` | Modified | Catch in-batch duplicates before insert/resolve flows. |
| `src/services/data_service.py` | Modified | Add global-safe DB loading path for all accounts. |
| `src/ui/pages/analytics_page.py` | Modified | Stop calling bank-only loaders with `None`. |
| `src/services/manual_entry_service.py` | Modified | Read categories from `rules[*].set.expense`. |
| `src/ui/flet_ui/rule_hub_view.py` | Modified | Use canonical categories and real retraining result messaging. |
| `src/services/rule_service.py` | Modified | Expose merge + retrain behavior for Flet consumers. |
| `tests/` | Modified | Add regression coverage for all six findings. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Hash identity change alters duplicate outcomes | Medium | Cover legacy/new cases with targeted DB and import-batch tests. |
| Global analytics fix drifts from existing bank filters | Low | Reuse shared query/filter helpers and add all-accounts tests. |

## Rollback Plan
Revert the implementation commit, restore prior Rule Hub merge messaging, and fall back to the previous dedup logic. If any rule-merge side effect occurs, recover `config/rules.yml` from the generated backup in `config/backups/` and rerun analytics/import smoke tests against the pre-change build.

## Dependencies
- Existing SQLite transaction schema and `config/rules.yml` canonical `set.expense` structure.

## Success Criteria
- [ ] Cross-account imports no longer collide on `source_hash`, while same-account duplicates still resolve correctly.
- [ ] Duplicate rows inside a single import batch are surfaced and not double-inserted.
- [ ] Global analytics renders from SQLite without `bank_id` validation failures.
- [ ] Manual entry and Flet Rule Hub show canonical categories from rule config.
- [ ] Flet rule merges retrain ML only on success and communicate the true result.
