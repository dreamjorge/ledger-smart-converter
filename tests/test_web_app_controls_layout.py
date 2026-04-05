import web_app


class _DummyColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyContainer:
    def __init__(self) -> None:
        self.columns_spec = None

    def columns(self, spec):
        self.columns_spec = spec
        return (_DummyColumn(), _DummyColumn(), _DummyColumn())


def test_global_controls_bar_uses_keyed_container_and_columns(monkeypatch) -> None:
    captured = {}
    container = _DummyContainer()

    def fake_container(key=None):
        captured["container_key"] = key
        return container

    monkeypatch.setattr(
        web_app,
        "_get_bank_selector_options",
        lambda: ({}, {"Santander": "santander_likeu"}, ["Santander"]),
    )
    monkeypatch.setattr(web_app.st, "container", fake_container)
    monkeypatch.setattr(
        web_app.st, "selectbox", lambda label, options, **kwargs: options[0]
    )
    monkeypatch.setattr(web_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app, "set_pref", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app.st, "rerun", lambda: None)
    web_app.st.session_state.lang = "es"
    web_app.st.session_state.active_user = "maria"
    web_app.st.session_state[web_app.BANK_KEY] = "Santander"

    web_app.render_global_controls_bar()

    assert captured["container_key"] == "global_controls"
    assert container.columns_spec == [2.2, 1.0, 1.2]


def test_main_renders_controls_bar_before_navigation(monkeypatch) -> None:
    call_order = []

    class _DummyNavigation:
        def run(self):
            call_order.append("run_navigation")

    def fake_controls_bar():
        call_order.append("render_controls")

    def fake_navigation(pages):
        call_order.append("create_navigation")
        return _DummyNavigation()

    monkeypatch.setattr(web_app, "load_css", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app, "render_global_controls_bar", fake_controls_bar)
    monkeypatch.setattr(web_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app.st, "Page", lambda *args, **kwargs: (args, kwargs))
    monkeypatch.setattr(web_app.st, "navigation", fake_navigation)

    web_app.main()

    assert call_order == ["render_controls", "create_navigation", "run_navigation"]
