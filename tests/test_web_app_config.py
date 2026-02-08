"""Tests for web_app.py configuration and mobile UX."""
import ast
from pathlib import Path

WEB_APP = Path(__file__).parent.parent / "src" / "web_app.py"


def _get_page_config_kwargs():
    """Parse web_app.py and extract st.set_page_config keyword arguments (literals only)."""
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "set_page_config"
        ):
            result = {}
            for kw in node.keywords:
                try:
                    result[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    pass  # skip non-literal args like t("page_title")
            return result
    return {}


def test_sidebar_expanded_on_mobile():
    """Sidebar must be expanded by default so mobile users see navigation."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("initial_sidebar_state") == "expanded", (
        "initial_sidebar_state should be 'expanded' so the sidebar is visible "
        "on mobile devices. 'auto' hides it and users can't find navigation."
    )


def test_page_config_layout_wide():
    """Wide layout gives more space on all screen sizes."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("layout") == "wide"


def test_render_mobile_tip_defined():
    """render_mobile_tip helper must exist for future use."""
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    fn_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "render_mobile_tip" in fn_names
