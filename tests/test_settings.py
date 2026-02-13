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
