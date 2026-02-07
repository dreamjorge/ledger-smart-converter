from pathlib import Path
import time

from services import import_service as imp


def test_resolve_output_paths_uses_target_mapping(tmp_path: Path):
    out_csv, out_unknown, out_suggestions = imp.resolve_output_paths(
        data_dir=tmp_path,
        bank_label="Santander LikeU",
        bank_id="santander_likeu",
        analytics_targets={"Santander LikeU": ("santander", "firefly_likeu.csv")},
    )
    assert out_csv == tmp_path / "santander" / "firefly_likeu.csv"
    assert out_unknown == tmp_path / "santander" / "unknown_merchants.csv"
    assert out_suggestions == tmp_path / "santander" / "rules_suggestions.yml"


def test_copy_csv_to_analysis_and_last_updated(tmp_path: Path):
    src = tmp_path / "src.csv"
    src.write_text("a,b\n1,2\n", encoding="utf-8")
    ok, result = imp.copy_csv_to_analysis(
        data_dir=tmp_path,
        analytics_targets={"BankX": ("x", "firefly_x.csv")},
        bank_label="BankX",
        csv_path=src,
    )
    assert ok is True
    copied = Path(result)
    assert copied.exists()
    time.sleep(0.01)
    updated = imp.get_csv_last_updated(copied)
    assert updated is not None
