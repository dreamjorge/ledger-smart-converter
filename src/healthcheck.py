#!/usr/bin/env python3

import importlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict

from settings import load_settings


def _check_dependency(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def run_healthcheck() -> Dict[str, object]:
    settings = load_settings()
    checks = {
        "config_exists": (settings.config_dir / "rules.yml").exists(),
        "data_dir_writable": _is_writable(settings.data_dir),
        "temp_dir_writable": _is_writable(settings.temp_dir),
        "dep_pandas": _check_dependency("pandas"),
        "dep_yaml": _check_dependency("yaml"),
        "dep_streamlit": _check_dependency("streamlit"),
        "dep_fitz": _check_dependency("fitz"),
        "dep_pytesseract": _check_dependency("pytesseract"),
        "tesseract_binary_found": bool(settings.ocr_tesseract_cmd) or shutil.which("tesseract") is not None,
    }
    ok = all(v for v in checks.values() if isinstance(v, bool))
    return {
        "ok": ok,
        "root_dir": str(settings.root_dir),
        "config_dir": str(settings.config_dir),
        "data_dir": str(settings.data_dir),
        "checks": checks,
    }


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".healthcheck_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def main() -> int:
    result = run_healthcheck()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
