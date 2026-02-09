from settings import load_settings


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("LSC_ROOT_DIR", "/tmp/lsc_root")
    monkeypatch.setenv("LSC_CONFIG_DIR", "/tmp/lsc_root/cfg")
    monkeypatch.setenv("LSC_DATA_DIR", "/tmp/lsc_root/data")
    monkeypatch.setenv("LSC_TEMP_DIR", "/tmp/lsc_root/tmp")
    monkeypatch.setenv("LSC_TESSERACT_CMD", "/usr/bin/tesseract")
    monkeypatch.setenv("LSC_LOG_LEVEL", "DEBUG")

    s = load_settings()
    assert str(s.root_dir) == "/tmp/lsc_root"
    assert str(s.config_dir) == "/tmp/lsc_root/cfg"
    assert str(s.data_dir) == "/tmp/lsc_root/data"
    assert str(s.temp_dir) == "/tmp/lsc_root/tmp"
    assert s.ocr_tesseract_cmd == "/usr/bin/tesseract"
    assert s.log_level == "DEBUG"
