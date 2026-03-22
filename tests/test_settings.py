from pathlib import Path

from settings import load_settings


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("LSC_ROOT_DIR", "/tmp/lsc_root")
    monkeypatch.setenv("LSC_CONFIG_DIR", "/tmp/lsc_root/cfg")
    monkeypatch.setenv("LSC_DATA_DIR", "/tmp/lsc_root/data")
    monkeypatch.setenv("LSC_TEMP_DIR", "/tmp/lsc_root/tmp")
    monkeypatch.setenv("LSC_TESSERACT_CMD", "/usr/bin/tesseract")
    monkeypatch.setenv("LSC_LOG_LEVEL", "DEBUG")

    s = load_settings()
    assert s.root_dir == Path("/tmp/lsc_root")
    assert s.config_dir == Path("/tmp/lsc_root/cfg")
    assert s.data_dir == Path("/tmp/lsc_root/data")
    assert s.temp_dir == Path("/tmp/lsc_root/tmp")
    assert s.ocr_tesseract_cmd == "/usr/bin/tesseract"
    assert s.log_level == "DEBUG"


def test_firefly_settings_default_to_none(monkeypatch):
    monkeypatch.delenv("FIREFLY_URL", raising=False)
    monkeypatch.delenv("FIREFLY_TOKEN", raising=False)
    s = load_settings()
    assert s.firefly_url is None
    assert s.firefly_token is None


def test_firefly_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("FIREFLY_URL", "http://my-firefly.local")
    monkeypatch.setenv("FIREFLY_TOKEN", "mytoken123")
    s = load_settings()
    assert s.firefly_url == "http://my-firefly.local"
    assert s.firefly_token == "mytoken123"


def test_load_settings_reads_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("LSC_LOG_LEVEL", raising=False)
    monkeypatch.delenv("LSC_DOTENV_PATH", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "LSC_LOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    s = load_settings()
    assert s.log_level == "WARNING"
