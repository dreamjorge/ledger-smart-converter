# Streamlit Global Controls Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move global bank/language/user controls from the sidebar into a responsive header controls bar while keeping native Streamlit navigation stable.

**Architecture:** Keep `src/web_app.py` as the single owner of application shell state and page routing. Use a header-level controls row for global context, preserve `st.navigation` for page routing, and harden the shell with tests that validate layout, contracts, and CSS safety.

**Tech Stack:** Python 3.11, Streamlit, pytest, CSS, existing session-state patterns in `src/web_app.py`

---

### Task 1: Lock the current sidebar contract with failing tests

**Files:**
- Modify: `tests/test_web_app_config.py`
- Test: `tests/test_web_app_config.py`

**Step 1: Write the failing test**

Add assertions that `web_app.py` no longer uses `st.sidebar.selectbox` for language/bank controls and still uses `st.navigation`.

```python
def test_global_controls_are_not_rendered_in_sidebar():
    source = WEB_APP.read_text(encoding="utf-8")
    assert 'st.sidebar.selectbox' not in source
```

**Step 2: Run test to verify it fails**

Run: `powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_web_app_config.py -q"`

Expected: FAIL because the current shell still renders selectboxes in the sidebar.

**Step 3: Keep the rest of the existing shell tests intact**

Do not weaken checks for:

- `initial_sidebar_state="auto"`
- `layout="wide"`
- native `st.navigation`

**Step 4: Commit**

```bash
git add tests/test_web_app_config.py
git commit -m "test: lock streamlit shell sidebar contract"
```

### Task 2: Add header controls shell tests

**Files:**
- Create: `tests/test_web_app_controls_layout.py`
- Test: `tests/test_web_app_controls_layout.py`

**Step 1: Write the failing test**

Create focused tests that parse `src/web_app.py` source and assert:

- a dedicated controls helper exists (for example `render_global_controls_bar`)
- language and bank controls are rendered outside the sidebar
- the user summary is rendered in the shell, not in a page module

```python
def test_global_controls_bar_helper_exists():
    source = WEB_APP.read_text(encoding="utf-8")
    assert 'def render_global_controls_bar' in source
```

**Step 2: Run test to verify it fails**

Run: `powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_web_app_controls_layout.py -q"`

Expected: FAIL because the helper does not exist yet.

**Step 3: Keep tests implementation-agnostic where possible**

Test shell structure and ownership, not fragile exact markup.

**Step 4: Commit**

```bash
git add tests/test_web_app_controls_layout.py
git commit -m "test: add streamlit controls bar shell checks"
```

### Task 3: Extract a dedicated global controls bar in the app shell

**Files:**
- Modify: `src/web_app.py`
- Test: `tests/test_web_app_config.py`
- Test: `tests/test_web_app_controls_layout.py`

**Step 1: Write minimal implementation**

Add a shell helper, for example:

```python
def render_global_controls_bar() -> None:
    col_bank, col_lang, col_user = st.columns([2.2, 1.0, 1.2])
    ...
```

Move the existing language and bank selection logic into this helper while preserving:

- `BANK_KEY`
- `st.session_state.lang`
- `set_pref("lang", ...)`
- existing bank option resolution

**Step 2: Render the helper from `main()`**

Render it after the title/subtitle and before `st.navigation(...)`.

**Step 3: Remove sidebar-owned controls**

Delete sidebar `selectbox` usage and any sidebar-only user metadata blocks.

**Step 4: Run tests**

Run: `powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_web_app_config.py tests/test_web_app_controls_layout.py tests/test_web_app_page_contracts.py -q"`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/web_app.py tests/test_web_app_config.py tests/test_web_app_controls_layout.py
git commit -m "refactor: move streamlit global controls into header bar"
```

### Task 4: Add responsive controls-bar styling

**Files:**
- Modify: `src/ui/style.css`
- Test: `tests/test_streamlit_style_contracts.py`

**Step 1: Write the failing test**

Extend `tests/test_streamlit_style_contracts.py` with assertions for a dedicated controls-bar CSS hook, for example:

```python
def test_global_controls_bar_css_exists() -> None:
    content = STYLE_CSS.read_text(encoding="utf-8")
    assert '.global-controls-bar' in content
```

**Step 2: Run test to verify it fails**

Run: `powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_streamlit_style_contracts.py -q"`

Expected: FAIL until the new layout class exists.

**Step 3: Write minimal CSS**

Add a compact controls row with:

- desktop multi-column alignment
- wrapped tablet behavior
- stacked mobile behavior
- full-width touch targets on mobile
- no CSS that interferes with Streamlit header/sidebar internals

Suggested selectors:

```css
.global-controls-bar { ... }
.global-controls-card { ... }
@media (max-width: 768px) { ... }
```

**Step 4: Keep existing safety guardrails**

Do not reintroduce any CSS that hides the Streamlit header structure or sidebar toggle.

**Step 5: Run tests**

Run: `powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_streamlit_style_contracts.py -q"`

Expected: PASS.

**Step 6: Commit**

```bash
git add src/ui/style.css tests/test_streamlit_style_contracts.py
git commit -m "style: add responsive streamlit controls bar"
```

### Task 5: Verify page compatibility after shell refactor

**Files:**
- Test: `tests/test_web_app_page_contracts.py`
- Test: `tests/test_ui_pages_imports.py`
- Test: `tests/test_ui_parity_smoke.py`

**Step 1: Run focused compatibility tests**

Run:

```bash
powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_web_app_page_contracts.py tests/test_ui_pages_imports.py tests/test_ui_parity_smoke.py -q"
```

Expected: PASS.

**Step 2: If a test fails, fix the shell not the pages first**

The refactor should preserve existing page contracts rather than pushing layout concerns down into page modules.

**Step 3: Commit**

```bash
git add tests/test_web_app_page_contracts.py tests/test_ui_pages_imports.py tests/test_ui_parity_smoke.py
git commit -m "test: verify streamlit shell refactor compatibility"
```

### Task 6: Update UI documentation

**Files:**
- Modify: `docs/context/ui.qmd`

**Step 1: Update the shell contract**

Document that:

- sidebar is navigation-only
- global controls now live in the header bar
- responsive behavior differs by desktop/tablet/mobile

**Step 2: Mention the guardrails**

Include references to the new shell/layout tests.

**Step 3: Run a quick documentation sanity check**

Read the updated section and verify it matches the code paths in `src/web_app.py`.

**Step 4: Commit**

```bash
git add docs/context/ui.qmd
git commit -m "docs: update streamlit shell layout contract"
```

### Task 7: Final verification

**Files:**
- Modify: none unless fixes are needed
- Test: `tests/test_web_app_config.py`
- Test: `tests/test_web_app_controls_layout.py`
- Test: `tests/test_web_app_page_contracts.py`
- Test: `tests/test_streamlit_style_contracts.py`
- Test: `tests/test_ui_pages_imports.py`
- Test: `tests/test_ui_parity_smoke.py`

**Step 1: Run the full focused shell suite**

Run:

```bash
powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m pytest tests/test_web_app_config.py tests/test_web_app_controls_layout.py tests/test_web_app_page_contracts.py tests/test_streamlit_style_contracts.py tests/test_ui_pages_imports.py tests/test_ui_parity_smoke.py -q"
```

Expected: PASS.

**Step 2: Manual visual verification**

Run locally:

```bash
streamlit run src/web_app.py
```

Verify:

- desktop shows header controls bar above content
- sidebar contains navigation only
- bank switch updates page context
- analytics remains reachable
- mobile-width browser still exposes bank/language controls without depending on the sidebar

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: move streamlit global controls into responsive header"
```
