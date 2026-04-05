import web_app


def test_page_import_matches_render_import_page_contract(monkeypatch) -> None:
    captured = {}

    def fake_render_import_page(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        web_app,
        "_get_bank_context",
        lambda: ("Santander", "santander_likeu", {}),
    )
    monkeypatch.setattr(web_app, "get_import_use_case", lambda: object())
    monkeypatch.setattr(web_app, "get_sync_use_case", lambda: object())

    import ui.pages.import_page as import_page

    monkeypatch.setattr(import_page, "render_import_page", fake_render_import_page)

    web_app.page_import()

    assert captured["bank_id"] == "santander_likeu"
    assert captured["import_use_case"] is not None
    assert "sync_use_case" in captured
    assert captured["bank_key"] == web_app.BANK_KEY
    assert captured["copy_feedback_key"] == web_app.COPY_FEEDBACK_KEY


def test_page_analytics_matches_render_analytics_dashboard_contract(
    monkeypatch,
) -> None:
    captured = {}

    def fake_render_analytics_dashboard(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_app, "get_ml_engine", lambda: object())
    monkeypatch.setattr(web_app, "get_report_use_case", lambda: object())

    import ui.pages.analytics_page as analytics_page

    monkeypatch.setattr(
        analytics_page,
        "render_analytics_dashboard",
        fake_render_analytics_dashboard,
    )

    web_app.page_analytics()

    assert captured["ml_engine"] is not None
    assert captured["report_use_case"] is not None
    assert captured["copy_feedback_key"] == web_app.COPY_FEEDBACK_KEY


def test_page_manual_matches_render_manual_entry_page_contract(monkeypatch) -> None:
    captured = {}

    def fake_render_manual_entry_page(**kwargs):
        captured.update(kwargs)

    import ui.pages.manual_entry_page as manual_entry_page

    monkeypatch.setattr(
        manual_entry_page,
        "render_manual_entry_page",
        fake_render_manual_entry_page,
    )
    web_app.st.session_state.lang = "es"
    web_app.st.session_state.active_user = "maria"

    web_app.page_manual()

    assert captured["config_dir"] == web_app.CONFIG_DIR
    assert captured["lang"] == "es"
    assert captured["user_id"] == "maria"


def test_page_settings_matches_render_settings_page_contract(monkeypatch) -> None:
    captured = {}

    def fake_render_settings_page(**kwargs):
        captured.update(kwargs)

    import ui.pages.settings_page as settings_page

    monkeypatch.setattr(
        settings_page,
        "render_settings_page",
        fake_render_settings_page,
    )
    web_app.st.session_state.active_user = "maria"

    web_app.page_settings()

    assert captured["t"] is web_app.t
    assert captured["active_user"] == "maria"
