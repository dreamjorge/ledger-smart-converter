from pathlib import Path

import healthcheck as hc
from settings import Settings


def test_run_healthcheck_with_monkeypatched_dependencies(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "rules.yml").write_text("version: 1\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(
        hc,
        "load_settings",
        lambda: Settings(
            root_dir=tmp_path,
            config_dir=cfg,
            data_dir=data_dir,
            temp_dir=temp_dir,
            ocr_tesseract_cmd="",
            log_level="INFO",
        ),
    )
    monkeypatch.setattr(hc, "_check_dependency", lambda _name: True)
    monkeypatch.setattr(hc.shutil, "which", lambda _cmd: "/usr/bin/tesseract")

    out = hc.run_healthcheck()
    assert out["ok"] is True
    assert out["checks"]["config_exists"] is True
    assert out["checks"]["tesseract_binary_found"] is True
