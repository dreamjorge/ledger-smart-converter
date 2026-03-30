# Proposal: Improve Web Page

## Intent
Modernize the Ledger Smart Converter web interface to provide a more native, fluid, and maintainable user experience using Streamlit's latest navigation and status features.

## Scope

### In Scope
- **Navigation Modernization**: Implement `st.navigation` and `st.Page` in `src/web_app.py`.
- **UI/UX Refinement**:
    - Refactor the import workflow to use `st.status` for real-time feedback.
    - Modularize `import_page.py` and `analytics_page.py` by extracting UI components.
    - Improve the "Rule Hub" interface in the analytics page.
- **Visual Consistency**: Audit and refine `src/ui/style.css` for better integration with native Streamlit components.

### Out of Scope
- Backend logic changes in `services/` (unless strictly required for UI state).
- New data sources or bank importers.
- Migrating to a different framework (e.g., Flet, though it exists in the repo, we stay on Streamlit).

## Approach
We will adopt a modular approach, starting with the navigation restructure to establish a solid foundation. Then, we will incrementally refactor the main pages (Import and Analytics) to use smaller, reusable components from `src/ui/components/`. We will replace the current manual radio-button navigation with the native Streamlit navigation system.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/web_app.py` | Modified | Navigation and layout overhaul. |
| `src/ui/pages/import_page.py` | Modified | Refactored into components, use `st.status`. |
| `src/ui/pages/analytics_page.py` | Modified | Refactored into components, improved Rule Hub. |
| `src/ui/style.css` | Modified | Styling refinements for native components. |
| `src/ui/components/` | New | New reusable UI components. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Session state loss | Medium | Explicitly pass or use global session state keys. |
| CSS conflicts | Low | Use more specific selectors or adjust variables. |
| Navigation regression | Low | Verify all existing page features work in new nav. |

## Rollback Plan
Revert changes to `src/web_app.py` and the modified page files using git. The project structure remains compatible with the previous state.

## Dependencies
- Streamlit 1.31.0+ (required for `st.navigation` and `st.Page`).

## Success Criteria
- [ ] Native-looking sidebar or top-bar navigation is functional.
- [ ] Import process provides clearer feedback via `st.status`.
- [ ] Codebase for pages is more modular and easier to maintain.
- [ ] Mobile and desktop views remain fully responsive and visually polished.
