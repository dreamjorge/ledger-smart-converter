import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:  # pragma: no cover
    def _load_dotenv(*args, **kwargs):
        dotenv_path = kwargs.get("dotenv_path")
        if not dotenv_path:
            return False

        path = Path(dotenv_path)
        if not path.exists():
            return False

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        return True


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    config_dir: Path
    data_dir: Path
    temp_dir: Path
    ocr_tesseract_cmd: str
    log_level: str


def load_settings() -> Settings:
    # Explicit local .env loading keeps CLI and Streamlit behavior consistent.
    dotenv_path = Path(os.getenv("LSC_DOTENV_PATH", ".env"))
    _load_dotenv(dotenv_path=dotenv_path, override=False)

    root_dir = Path(os.getenv("LSC_ROOT_DIR", Path(__file__).resolve().parents[1]))
    config_dir = Path(os.getenv("LSC_CONFIG_DIR", root_dir / "config"))
    data_dir = Path(os.getenv("LSC_DATA_DIR", root_dir / "data"))
    temp_dir = Path(os.getenv("LSC_TEMP_DIR", root_dir / "temp_web_uploads"))
    return Settings(
        root_dir=root_dir,
        config_dir=config_dir,
        data_dir=data_dir,
        temp_dir=temp_dir,
        ocr_tesseract_cmd=os.getenv("LSC_TESSERACT_CMD", ""),
        log_level=os.getenv("LSC_LOG_LEVEL", "INFO"),
    )
