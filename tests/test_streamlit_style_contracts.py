from pathlib import Path


STYLE_CSS = Path(__file__).parent.parent / "src" / "ui" / "style.css"


def test_global_controls_bar_css_exists() -> None:
    content = STYLE_CSS.read_text(encoding="utf-8")

    assert ".st-key-global_controls" in content


def test_streamlit_header_container_is_not_hidden() -> None:
    content = STYLE_CSS.read_text(encoding="utf-8")

    assert 'header[data-testid="stHeader"]>div:first-child' not in content
    assert "height: 3rem !important;" not in content


def test_sidebar_collapse_button_stays_visible() -> None:
    content = STYLE_CSS.read_text(encoding="utf-8")

    assert '[data-testid="stSidebarCollapse"]' in content
    assert "visibility: visible !important;" in content


def test_style_contract_avoids_brittle_global_shell_selectors() -> None:
    content = STYLE_CSS.read_text(encoding="utf-8")

    assert '[class*="css"]' not in content
    assert '[data-testid="stHorizontalBlock"]' not in content
    assert '.st-key-global_controls [data-testid="column"]' not in content
    assert '[data-testid="stSidebar"] > div:first-child' not in content
