## Exploration: Improve Web Page

### Current State
The web application is a Streamlit app with a custom dark theme (Outfit font, primary blue/indigo colors). It uses a horizontal `st.radio` component for navigation between four main pages: Import, Analytics, Manual Entry, and Settings. The code is modularized into pages and components, but page functions are relatively large and mix UI logic with service calls. Styling is handled via a comprehensive `src/ui/style.css` file which includes responsive design and touch-friendly optimizations.

### Affected Areas
- `src/web_app.py` — Main entry point, navigation logic, and layout.
- `src/ui/pages/import_page.py` — Import process UI, file uploaders, and deduplication review.
- `src/ui/pages/analytics_page.py` — Dashboard, charts, and Rule Hub.
- `src/ui/style.css` — Global styling and responsive adjustments.
- `src/ui/components/` — Potential for new reusable components.

### Approaches
1. **Modernize Navigation & Layout** — Switch to native `st.navigation` and `st.Page` structure. This provides better URL handling, native sidebar/topbar navigation, and cleaner entry point logic.
   - Pros: Native look and feel, better state management, simplified `web_app.py`.
   - Cons: Requires reorganizing file structure or page function calls.
   - Effort: Medium

2. **UI/UX Polish & Componentization** — Refactor large page functions into smaller components in `src/ui/components/`. Implement `st.status` for the import workflow and improve the "Rule Hub" presentation.
   - Pros: Better maintainability, cleaner UI, improved feedback for long-running tasks.
   - Cons: Significant refactoring of existing page logic.
   - Effort: Medium

3. **Enhanced Visualizations & Unified Dashboard** — Improve Plotly charts in the analytics page and create a unified "Global Overview" that doesn't require switching between banks.
   - Pros: More value for the user, better insights, more modern dashboard feel.
   - Cons: Requires complex data aggregation across multiple CSVs/DB tables.
   - Effort: High

### Recommendation
I recommend a combined approach: **Modernize Navigation (Option 1)** and **UI/UX Polish (Option 2)**. This will provide the most immediate value in terms of "feeling" like a modern web app while also improving the developer experience and maintainability.

### Risks
- **Breaking Session State**: Changing navigation structure might affect how `st.session_state` is preserved between pages if not handled carefully.
- **CSS Conflicts**: New Streamlit native components might have different DOM structures that conflict with existing custom CSS.

### Ready for Proposal
Yes — I have a clear understanding of the current structure and how to modernize it using Streamlit's latest features.
