# UI Specification Delta: Improve Web Page

## Purpose
This specification defines the modernized UI requirements for the Ledger Smart Converter, transitioning to native Streamlit navigation and enhancing the import/analytics user experience.

## MODIFIED Requirements

### Requirement: Native Navigation System
The application MUST use Streamlit's native `st.navigation` and `st.Page` system instead of the manual `st.radio` navigation.
(Previously: Navigation was handled by a custom `st.radio` component in `web_app.py`.)

#### Scenario: Navigate between pages
- GIVEN the application is loaded
- WHEN the user selects "Analytics" from the native sidebar/navigation
- THEN the application SHALL render the analytics page
- AND the URL SHOULD update to reflect the current page

### Requirement: Import Feedback via st.status
The import process MUST use the `st.status` container to provide real-time updates for each stage of the import (saving, parsing, validating, categorizing, and deduping).
(Previously: Import status was shown via a single `st.spinner` and a final `st.success` message.)

#### Scenario: Successful bank import
- GIVEN the user has uploaded a valid bank file
- WHEN the user clicks "Process Files"
- THEN the system SHALL show an `st.status` container
- AND it SHALL display individual steps (e.g., "Parsing statement...", "Applying rules...")
- AND finally it SHALL show a completion message within the status container

### Requirement: Modular Page Structure
Page logic in `import_page.py` and `analytics_page.py` SHOULD be refactored into smaller, reusable components located in `src/ui/components/`.
(Previously: Page functions were large and contained most of the UI and minor logic.)

#### Scenario: Render analytics dashboard
- GIVEN the analytics page is active
- WHEN the dashboard is rendered
- THEN it SHALL invoke modular component functions (e.g., `render_metrics`, `render_charts`)
- AND each component SHALL independently handle its own rendering logic

### Requirement: Enhanced Rule Hub
The Rule Hub in the analytics page MUST be improved to provide a more intuitive merchant lookup and rule staging experience.
(Previously: The Rule Hub was a dense expander with many inputs and buttons.)

#### Scenario: Stage a new categorization rule
- GIVEN the user is in the Analytics page's Rule Hub
- WHEN the user selects a merchant and a target category
- THEN the system SHALL provide an immediate "Stage Rule" action
- AND it SHALL clearly indicate the number of pending rules to be applied

## ADDED Requirements

### Requirement: Unified Global Dashboard
The analytics page SHOULD provide a "Global Overview" option that aggregates data from all configured bank accounts when no specific bank is selected or via a dedicated view.

#### Scenario: View global spending
- GIVEN the user is on the Analytics page
- WHEN the user selects "All Accounts" or the global view
- THEN the system SHALL aggregate transactions from all local databases/CSVs
- AND it SHALL render combined metrics and charts

## Success Criteria
- [ ] Navigation is handled by `st.navigation`.
- [ ] Import workflow uses `st.status`.
- [ ] Pages are decomposed into components in `src/ui/components/`.
- [ ] Rule Hub is visually cleaner and functionally more intuitive.
