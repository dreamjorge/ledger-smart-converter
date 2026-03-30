# Design: Improve Web Page

## Technical Approach
We will modernize the web interface by adopting Streamlit's native navigation system and refactoring the existing monolithic page functions into reusable, modular components. This approach establishes a cleaner separation of concerns and improves the real-time user feedback loop during long-running import tasks.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|----------|--------|-------------------------|-----------|
| Navigation System | `st.navigation` + `st.Page` | Custom `st.radio`, custom `st.sidebar` buttons | Provides a native look, handled URLs, and cleaner `web_app.py`. |
| Import Feedback | `st.status` | `st.spinner`, progressive `st.write` | Offers a more professional and grouped real-time feedback container. |
| Page Modularization | Component functions in `src/ui/components/` | Inline code, separate modules per page | Enhances code reusability and reduces the cognitive load of large page files. |
| Navigation Layout | Native Sidebar | Native Top-bar | The sidebar is standard for desktop; Streamlit handles the transition to a hamburger menu on mobile. |

## Data Flow

    [web_app.py] (Entry Point)
        │
        ├─── [st.navigation] (Routing)
        │       │
        │       ├─── [Import Page] ──→ [import_service] ──→ [st.status] (UI Progress)
        │       │                      └─ [import_components]
        │       │
        │       ├─── [Analytics Page] ──→ [analytics_service] ──→ [Plotly Charts]
        │       │                         ├─ [analytics_components]
        │       │                         └─ [rule_components] (Rule Hub)
        │       │
        │       └─── [Settings/Manual] ──→ [user_service]

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/web_app.py` | Modify | Implement `st.navigation` and `st.Page` routing. |
| `src/ui/pages/import_page.py` | Modify | Refactor to use `st.status` and extract components. |
| `src/ui/pages/analytics_page.py` | Modify | Refactor to extract `Rule Hub` into separate components. |
| `src/ui/components/import_components.py` | Create | New components for file uploaders and results rendering. |
| `src/ui/components/rule_components.py` | Create | New components for the "Rule Hub" UI. |
| `src/ui/style.css` | Modify | Refine styling for native Streamlit components. |

## Interfaces / Contracts

The page rendering functions will move to a standard `st.Page` structure:

```python
# src/web_app.py
pg = st.navigation({
    "Main": [
        st.Page("ui/pages/import_page.py", title=t("nav_import"), icon="📥"),
        st.Page("ui/pages/analytics_page.py", title=t("nav_analytics"), icon="📊"),
    ],
    "Settings": [
        st.Page("ui/pages/settings_page.py", title=t("nav_settings"), icon="⚙️"),
    ]
})
pg.run()
```

The import status implementation:

```python
# src/ui/pages/import_page.py
with st.status(t("processing_status"), expanded=True) as status:
    st.write(t("step_parsing"))
    # ... call service
    status.update(label=t("step_complete"), state="complete", expanded=False)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Component rendering | Use `pytest` to verify component functions don't crash and receive correct inputs. |
| Integration | Page Navigation | Verify that `st.session_state` is preserved across different pages. |
| E2E | Manual UI Verification | Walk through the import and analytics process to ensure `st.status` and charts work as expected. |

## Migration / Rollout
No data migration required. The change is strictly a UI/UX refactor.

## Open Questions
- [ ] Should we keep the "Bank Selector" in the top bar or move it inside the pages? (Recommendation: Keep it global in `st.session_state` via sidebar).
