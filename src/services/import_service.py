import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ImportRunResult:
    returncode: int
    stdout: str
    stderr: str
    out_csv: Path
    out_unknown: Path
    out_suggestions: Path


def save_uploaded_file(uploaded_file, temp_dir: Path, subdir: str = "uploads") -> Optional[Path]:
    if uploaded_file is None:
        return None
    dest_dir = temp_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / uploaded_file.name
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path


def resolve_output_paths(
    data_dir: Path,
    bank_label: str,
    bank_id: str,
    analytics_targets: Dict[str, Tuple[str, str]],
) -> Tuple[Path, Path, Path]:
    analytics_target = analytics_targets.get(bank_label)
    if not analytics_target:
        analytics_target = (bank_id, f"firefly_{bank_id}.csv")
    dest_dir, dest_name = analytics_target
    out_csv = data_dir / dest_dir / dest_name
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_unknown = data_dir / dest_dir / "unknown_merchants.csv"
    out_suggestions = data_dir / dest_dir / "rules_suggestions.yml"
    return out_csv, out_unknown, out_suggestions


def run_import_script(
    root_dir: Path,
    src_dir: Path,
    bank_id: str,
    rules_path: Path,
    out_csv: Path,
    out_unknown: Path,
    main_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
    force_pdf_ocr: bool = False,
    strict: bool = False,
) -> ImportRunResult:
    args = [
        "--bank", bank_id,
        "--rules", str(rules_path),
        "--out", str(out_csv),
        "--unknown-out", str(out_unknown),
    ]
    if main_path:
        args.extend(["--data", str(main_path)])
    if pdf_path:
        args.extend(["--pdf", str(pdf_path)])
    if force_pdf_ocr:
        args.append("--pdf-source")
    if strict:
        args.append("--strict")

    cmd = [sys.executable, str(src_dir / "generic_importer.py")] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root_dir))
    result = ImportRunResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        out_csv=out_csv,
        out_unknown=out_unknown,
        out_suggestions=out_csv.parent / "rules_suggestions.yml",
    )
    if proc.returncode == 0:
        try:
            from ml_categorizer import train_global_model
            train_global_model()
        except Exception as exc:
            logger.warning("ML retrain after import failed: %s", exc)
    return result


def copy_csv_to_analysis(
    data_dir: Path,
    analytics_targets: Dict[str, Tuple[str, str]],
    bank_label: str,
    csv_path: Path,
    bank_id: Optional[str] = None,
) -> Tuple[bool, str]:
    target = analytics_targets.get(bank_label)
    if not target and bank_id:
        target = (bank_id, f"firefly_{bank_id}.csv")
    if not target:
        return False, "unknown_bank"
    if not csv_path or not Path(csv_path).exists():
        return False, "missing_src"

    dest_dir, dest_name = target
    dest_path = data_dir / dest_dir / dest_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    src_path = Path(csv_path).resolve()
    dest_resolved = dest_path.resolve()
    if src_path != dest_resolved:
        shutil.copy(src_path, dest_resolved)
    return True, str(dest_resolved)


_FALLBACK_BANKS = {
    "santander_likeu": {"display_name": "Santander LikeU (XLSX/PDF)", "type": "xlsx"},
    "hsbc": {"display_name": "HSBC Mexico (XML/PDF)", "type": "xml"},
}


def get_banks_from_config(rules_path: Path) -> Dict[str, Dict]:
    """Return {bank_id: {"display_name": ..., "type": ...}} from rules.yml banks section.

    Falls back to the two built-in banks if the file is missing or has no banks key.
    """
    if rules_path.exists():
        try:
            cfg = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
            banks = cfg.get("banks", {})
            if banks:
                return {
                    bid: {
                        "display_name": bcfg.get("display_name", bid),
                        "type": bcfg.get("type", "xlsx"),
                    }
                    for bid, bcfg in banks.items()
                }
        except Exception:
            pass
    return dict(_FALLBACK_BANKS)


def get_csv_last_updated(path: Path) -> Optional[str]:
    if not path:
        return None
    if not path.exists():
        return None
    ts = datetime.fromtimestamp(path.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M:%S")
