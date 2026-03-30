# Tasks: Improve Web Page

## Phase 1: Foundation (UI Components)

- [x] 1.1 Create `src/ui/components/import_components.py` and extract `render_file_uploaders` and `render_import_results` from `import_page.py`.
- [x] 1.2 Extract `render_dedup_review` into `src/ui/components/import_components.py` to handle duplicate resolution UI.
- [x] 1.3 Create `src/ui/components/rule_components.py` and extract `render_rule_staging_hub` from `analytics_page.py`.
- [x] 1.4 Implement `render_pending_rules_summary` in `src/ui/components/rule_components.py` for clearer feedback on staged changes.

## Phase 2: Core Refactor (Page Logic)

- [x] 2.1 Refactor `src/ui/pages/import_page.py` to implement `st.status` for the import workflow steps (parsing, rules, dedup).
- [x] 2.2 Update `src/ui/pages/import_page.py` to use modular components from `src/ui/components/import_components.py`.
- [x] 2.3 Refactor `src/ui/pages/analytics_page.py` to use `render_rule_staging_hub` from `src/ui/components/rule_components.py`.
- [x] 2.4 Add "Global Overview" logic to `src/ui/pages/analytics_page.py` to aggregate data across all bank accounts when selected.

## Phase 3: Integration (Navigation & Layout)

- [x] 3.1 Modify `src/web_app.py` to implement `st.navigation` and `st.Page` routing as defined in the design.
- [x] 3.2 Move global controls (Language select, Bank selector) to the `st.sidebar` for consistent access across pages.
- [x] 3.3 Ensure `st.session_state` keys (e.g., `active_user`, `lang`) are correctly preserved in the new navigation structure.

## Phase 4: Styling & Polish

- [x] 4.1 Update `src/ui/style.css` to ensure custom dark theme integrates seamlessly with native Streamlit navigation elements.
- [x] 4.2 Polish `st.status` step labels and transition animations for a smoother "alive" feel.

## Phase 5: Verification & Testing

- [x] 5.1 Verify that navigating between all pages (Import, Analytics, Manual, Settings) updates the URL and preserves state.
- [x] 5.2 Test the full import workflow for both Santander and HSBC, ensuring `st.status` steps complete correctly.
- [x] 5.3 Verify Rule Hub staging, merging, and subsequent ML retraining feedback.
- [x] 5.4 Perform responsive design check on mobile view to ensure sidebar navigation and charts scale properly.
