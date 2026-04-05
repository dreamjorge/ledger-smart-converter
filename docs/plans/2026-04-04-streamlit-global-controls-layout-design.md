# Streamlit Global Controls Layout Design

**Date:** 2026-04-04

## Goal

Move global UI controls out of the Streamlit sidebar so page navigation remains stable and users can always switch bank context and language on desktop and mobile.

## Problem

The current Streamlit shell mixes two different concerns in the same sidebar:

- app navigation via `st.navigation`
- global context controls like bank and language selection

This creates a fragile interaction model. If the sidebar collapses, breaks visually, or becomes partially hidden by CSS, users lose both navigation and context controls at the same time. That is exactly the kind of coupling that makes the UI feel brittle.

## Approved Direction

Use the following layout contract:

- `Sidebar`: navigation only
- `Header controls bar`: global controls only
- `Page body`: page-specific content only

This preserves Streamlit's native routing while making the most important global controls always accessible.

## Layout Architecture

### 1. App Shell

The app shell in `src/web_app.py` remains the single place that owns:

- `st.navigation` page registration
- global session state initialization
- top-level layout structure

The app shell must render in this order:

1. title / subtitle
2. global controls bar
3. native Streamlit navigation
4. selected page content

### 2. Sidebar Role

The sidebar must contain only native page navigation.

Allowed in sidebar:

- `st.navigation`
- page icons/titles handled by Streamlit

Not allowed in sidebar:

- bank selector
- language selector
- active user status blocks with large visual weight
- explanatory text blocks
- decorative info cards

This keeps the sidebar narrow, stable, and predictable.

### 3. Global Controls Bar

The controls bar lives in the main page area, immediately below the app title.

It contains exactly three global elements:

- `Bank selector` — primary control
- `Language selector` — secondary compact control
- `Active user summary` — informational only

These controls remain owned by `src/web_app.py` and continue to use the existing session-state keys:

- `bank_select`
- `lang`
- `active_user`

No page should redefine or duplicate these controls.

## Responsive Behavior

### Desktop

- Sidebar stays narrow and visually quiet.
- Controls bar renders in a 3-column layout.
- Bank selector gets the most width.
- Language selector stays compact.
- User summary stays light and non-dominant.

### Tablet

- Sidebar remains available.
- Controls bar wraps to a 2-column or 2+1 arrangement as needed.
- Bank selector remains first in visual hierarchy.

### Mobile

- Sidebar may collapse freely.
- Controls bar remains visible above page content.
- Controls stack vertically in this order:
  1. bank selector
  2. language selector
  3. active user
- Controls use full-width touch-friendly sizing.

## Visual Rules

- The controls bar should look like a compact tool row, not a second hero section.
- The bank selector is the dominant element.
- The user indicator must not compete with page content.
- The controls bar should reduce friction, not increase page height excessively.

## Safety Rules

To avoid repeating the current UI regression class:

- Do not hide structural Streamlit header containers with CSS.
- Do not move native navigation responsibilities into custom tabs.
- Do not write widget state after widget instantiation.
- Do not duplicate global controls inside individual pages.
- Keep layout CSS cosmetic; do not disable native Streamlit affordances.

## Testing Strategy

The new layout should be protected by tests that verify:

- `web_app.py` still uses `st.navigation`
- page wrappers keep their renderer contracts intact
- global controls no longer live in the sidebar
- the CSS does not hide Streamlit's sidebar toggle/header affordances
- layout rules for the global controls bar remain present

## Affected Files

- `src/web_app.py` — move global controls into main header area
- `src/ui/style.css` — controls bar styling and responsive behavior
- `tests/test_web_app_config.py` — update shell expectations
- `tests/test_web_app_page_contracts.py` — keep wrapper contracts covered
- `tests/test_streamlit_style_contracts.py` — keep visibility and CSS guardrails covered
- `docs/context/ui.qmd` — document the new app shell contract

## Expected Outcome

After implementation:

- users can always switch bank and language without depending on sidebar visibility
- navigation remains stable and native
- desktop gains more content space
- mobile keeps critical controls reachable without fragile sidebar interactions
