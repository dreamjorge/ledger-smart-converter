# UI Specification Delta: Fix Flet Pre-Merge Regressions

## Purpose
This delta corrects verified regressions in deduplication, analytics drilldown, manual entry, and the Flet Rule Hub before the Flet migration is merged.

## MODIFIED Requirements

### Requirement: Unified Global Dashboard
The analytics experience MUST support an all-accounts database drilldown path and MUST NOT invoke bank-scoped loaders with an undefined bank identity.
(Previously: the global view aggregated data but did not define a database-safe all-accounts drilldown contract.)

#### Scenario: View all-accounts drilldown from SQLite
- GIVEN the user selects "All Accounts" in analytics
- WHEN the dashboard loads database-backed metrics and charts
- THEN the system SHALL aggregate transactions across all accounts
- AND it SHALL NOT pass `None` to a bank-only loader

### Requirement: Enhanced Rule Hub
The Flet Rule Hub MUST present canonical category options derived from the system taxonomy and MUST report retraining only when retraining actually completed successfully.
(Previously: category options could diverge from canonical values and merge messaging could imply retraining even when it did not occur.)

#### Scenario: Apply pending rules with retraining
- GIVEN the user merges pending rules from the Flet Rule Hub
- WHEN the merge succeeds and retraining completes
- THEN the system SHALL confirm that rules were applied and retraining occurred
- AND it SHALL use canonical taxonomy values in all category selectors

#### Scenario: Apply pending rules without retraining
- GIVEN the user triggers a merge from the Flet Rule Hub
- WHEN retraining is skipped, fails, or never starts
- THEN the system MUST NOT claim that retraining happened
- AND it SHALL communicate the actual merge outcome only

## ADDED Requirements

### Requirement: Account-Aware Deduplication Identity
The deduplication identity MUST include account context so that identical transaction payloads from different accounts are treated as distinct records, while same-account duplicates remain duplicates.

#### Scenario: Prevent cross-account hash collision
- GIVEN two transactions have the same date, amount, and description
- AND they belong to different accounts
- WHEN deduplication identity is evaluated
- THEN the system SHALL treat them as different records

#### Scenario: Preserve same-account duplicate detection
- GIVEN two transactions have the same deduplication fields
- AND they belong to the same account
- WHEN deduplication identity is evaluated
- THEN the system SHALL treat the second transaction as a duplicate

### Requirement: In-Batch Duplicate Detection
The deduplication workflow MUST detect duplicates that appear within the same import batch and MUST prevent both rows from being treated as unique inserts.

#### Scenario: Detect duplicate rows inside one batch
- GIVEN an import batch contains two identical same-account transactions
- WHEN the batch is validated for duplicates
- THEN the system SHALL surface the duplicate within that batch
- AND it SHALL prevent double insertion of the duplicated row

### Requirement: Manual Entry Category Source
Manual entry category selection MUST load expense categories from `rules[*].set.expense` so that manual classification uses the same canonical category source as rules and analytics.

#### Scenario: Load categories for manual entry
- GIVEN the manual entry form is opened
- WHEN category options are loaded
- THEN the system SHALL read canonical expense categories from `rules[*].set.expense`
- AND it SHALL exclude non-canonical placeholder values

### Requirement: Canonical Flet Category Taxonomy
Flet Rule Hub category selectors MUST use canonical taxonomy values only and SHOULD remain aligned with the category vocabulary used by rule configuration and downstream analytics.

#### Scenario: Render canonical category options
- GIVEN the user opens a category selector in the Flet Rule Hub
- WHEN the available categories are displayed
- THEN every option SHALL be a canonical taxonomy value
- AND the selector SHALL NOT show ad hoc or legacy aliases
