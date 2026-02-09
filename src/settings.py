import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    config_dir: Path
    data_dir: Path
    temp_dir: Path
    ocr_tesseract_cmd: str
    log_level: str


def load_settings() -> Settings:
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
