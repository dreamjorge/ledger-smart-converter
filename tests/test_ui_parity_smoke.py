import inspect

from services.manual_entry_service import load_categories_from_rules
from services.rules_config_service import load_expense_categories
from ui.flet_ui import analytics_view, manual_entry_view, rule_hub_view, settings_view
from ui.pages import analytics_page, manual_entry_page, settings_page
from services.user_service import set_active_user, verify_password


def test_streamlit_and_flet_expose_analytics_entrypoints() -> None:
    assert callable(analytics_page.render_analytics_dashboard)
    assert callable(analytics_view.get_analytics_view)

    streamlit_params = inspect.signature(
        analytics_page.render_analytics_dashboard
    ).parameters
    flet_params = inspect.signature(analytics_view.get_analytics_view).parameters

    assert {"t", "ml_engine"}.issubset(streamlit_params)
    assert {"page", "t", "config"}.issubset(flet_params)


def test_streamlit_and_flet_share_manual_entry_category_source() -> None:
    assert callable(manual_entry_page.render_manual_entry_page)
    assert callable(manual_entry_view.get_manual_entry_view)
    assert manual_entry_page.load_categories_from_rules is load_categories_from_rules
    assert manual_entry_view.load_categories_from_rules is load_categories_from_rules


def test_rule_hub_uses_canonical_manual_entry_category_loader() -> None:
    assert callable(rule_hub_view.get_rule_hub_view)
    assert callable(rule_hub_view.load_canonical_rule_hub_categories)

    rules_path_param = inspect.signature(
        rule_hub_view.load_canonical_rule_hub_categories
    ).parameters
    assert "rules_path" in rules_path_param
    assert (
        rule_hub_view.load_canonical_rule_hub_categories.__globals__[
            "load_expense_categories"
        ]
        is load_expense_categories
    )
    assert manual_entry_page.load_categories_from_rules is load_categories_from_rules
    assert manual_entry_view.load_categories_from_rules is load_categories_from_rules


def test_streamlit_and_flet_settings_expose_profile_switching_entrypoints() -> None:
    assert callable(settings_page.render_settings_page)
    assert callable(settings_view.get_settings_view)
    assert settings_page.verify_password is verify_password
    assert settings_view.verify_password is verify_password
    assert settings_page.set_active_user is set_active_user
    assert settings_view.set_active_user is set_active_user
