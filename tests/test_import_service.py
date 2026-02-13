from pathlib import Path
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock

from services import import_service as imp


# ===========================
# Existing Tests
# ===========================

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


# ===========================
# save_uploaded_file Tests
# ===========================

class TestSaveUploadedFile:
    """Test save_uploaded_file function."""

    def test_saves_file_to_uploads_subdir(self, tmp_path):
        """Test that file is saved to uploads subdirectory."""
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.getbuffer.return_value = b"test content"

        result = imp.save_uploaded_file(mock_file, tmp_path, subdir="uploads")

        assert result == tmp_path / "uploads" / "test.pdf"
        assert result.exists()
        assert result.read_bytes() == b"test content"

    def test_creates_subdirectory_if_not_exists(self, tmp_path):
        """Test that subdirectory is created if it doesn't exist."""
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.getbuffer.return_value = b"content"

        result = imp.save_uploaded_file(mock_file, tmp_path, subdir="nested/dir")

        assert result.parent.exists()
        assert result.exists()

    def test_returns_none_for_none_file(self, tmp_path):
        """Test that None is returned when uploaded_file is None."""
        result = imp.save_uploaded_file(None, tmp_path)
        assert result is None

    def test_uses_default_uploads_subdir(self, tmp_path):
        """Test that default 'uploads' subdir is used."""
        mock_file = Mock()
        mock_file.name = "file.csv"
        mock_file.getbuffer.return_value = b"data"

        result = imp.save_uploaded_file(mock_file, tmp_path)

        assert "uploads" in str(result)
        assert result.parent.name == "uploads"

    def test_handles_binary_content(self, tmp_path):
        """Test that binary content is preserved."""
        mock_file = Mock()
        mock_file.name = "binary.dat"
        binary_content = bytes([0x00, 0xFF, 0x42, 0xAB])
        mock_file.getbuffer.return_value = binary_content

        result = imp.save_uploaded_file(mock_file, tmp_path)

        assert result.read_bytes() == binary_content


# ===========================
# resolve_output_paths Tests (Additional)
# ===========================

class TestResolveOutputPathsEdgeCases:
    """Test edge cases for resolve_output_paths."""

    def test_handles_unknown_bank_with_fallback(self, tmp_path):
        """Test fallback behavior when bank_label not in targets."""
        out_csv, out_unknown, out_suggestions = imp.resolve_output_paths(
            data_dir=tmp_path,
            bank_label="Unknown Bank",
            bank_id="hsbc_credit",
            analytics_targets={},
        )

        # Should use full bank_id as fallback directory for consistent hierarchy
        assert out_csv == tmp_path / "hsbc_credit" / "firefly_hsbc_credit.csv"
        assert out_unknown == tmp_path / "hsbc_credit" / "unknown_merchants.csv"

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created."""
        out_csv, _, _ = imp.resolve_output_paths(
            data_dir=tmp_path,
            bank_label="Test",
            bank_id="test_bank",
            analytics_targets={"Test": ("testdir", "test.csv")},
        )

        # Parent should be created
        assert out_csv.parent.exists()


# ===========================
# run_import_script Tests
# ===========================

class TestRunImportScript:
    """Test run_import_script subprocess orchestration."""

    def test_builds_correct_command_with_all_args(self, tmp_path):
        """Test that command is built correctly with all arguments."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "success"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            root_dir = tmp_path / "root"
            src_dir = tmp_path / "src"
            rules_path = tmp_path / "rules.yml"
            out_csv = tmp_path / "out.csv"
            out_unknown = tmp_path / "unknown.csv"
            main_path = tmp_path / "main.xlsx"
            pdf_path = tmp_path / "doc.pdf"

            result = imp.run_import_script(
                root_dir=root_dir,
                src_dir=src_dir,
                bank_id="santander",
                rules_path=rules_path,
                out_csv=out_csv,
                out_unknown=out_unknown,
                main_path=main_path,
                pdf_path=pdf_path,
                force_pdf_ocr=True,
                strict=True,
            )

            # Verify subprocess.run was called
            assert mock_run.called
            call_args = mock_run.call_args[0][0]

            # Check command components
            assert "--bank" in call_args
            assert "santander" in call_args
            assert "--data" in call_args
            assert "--pdf" in call_args
            assert "--pdf-source" in call_args
            assert "--strict" in call_args

    def test_omits_optional_args_when_not_provided(self, tmp_path):
        """Test that optional arguments are omitted when not provided."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            imp.run_import_script(
                root_dir=tmp_path,
                src_dir=tmp_path / "src",
                bank_id="hsbc",
                rules_path=tmp_path / "rules.yml",
                out_csv=tmp_path / "out.csv",
                out_unknown=tmp_path / "unknown.csv",
                main_path=None,
                pdf_path=None,
                force_pdf_ocr=False,
                strict=False,
            )

            call_args = mock_run.call_args[0][0]

            # Should not have optional flags
            assert "--data" not in call_args
            assert "--pdf" not in call_args
            assert "--pdf-source" not in call_args
            assert "--strict" not in call_args

    def test_returns_import_run_result(self, tmp_path):
        """Test that ImportRunResult is returned with correct data."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Import completed"
            mock_result.stderr = "Warning: something"
            mock_run.return_value = mock_result

            out_csv = tmp_path / "output" / "result.csv"
            out_unknown = tmp_path / "output" / "unknown.csv"

            result = imp.run_import_script(
                root_dir=tmp_path,
                src_dir=tmp_path / "src",
                bank_id="test",
                rules_path=tmp_path / "rules.yml",
                out_csv=out_csv,
                out_unknown=out_unknown,
            )

            assert isinstance(result, imp.ImportRunResult)
            assert result.returncode == 0
            assert result.stdout == "Import completed"
            assert result.stderr == "Warning: something"
            assert result.out_csv == out_csv
            assert result.out_unknown == out_unknown

    def test_captures_subprocess_error(self, tmp_path):
        """Test that subprocess errors are captured."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error: file not found"
            mock_run.return_value = mock_result

            result = imp.run_import_script(
                root_dir=tmp_path,
                src_dir=tmp_path / "src",
                bank_id="test",
                rules_path=tmp_path / "rules.yml",
                out_csv=tmp_path / "out.csv",
                out_unknown=tmp_path / "unknown.csv",
            )

            assert result.returncode == 1
            assert "Error" in result.stderr


# ===========================
# copy_csv_to_analysis Tests (Additional)
# ===========================

class TestCopyCsvToAnalysisEdgeCases:
    """Test edge cases for copy_csv_to_analysis."""

    def test_returns_false_for_unknown_bank(self, tmp_path):
        """Test that False is returned for unknown bank."""
        src = tmp_path / "src.csv"
        src.write_text("data", encoding="utf-8")

        ok, msg = imp.copy_csv_to_analysis(
            data_dir=tmp_path,
            analytics_targets={},
            bank_label="Unknown Bank",
            csv_path=src,
        )

        assert ok is False
        assert msg == "unknown_bank"

    def test_uses_bank_id_fallback_for_unknown_bank_label(self, tmp_path):
        """Test fallback copy path when bank_label is not mapped but bank_id is known."""
        src = tmp_path / "src.csv"
        src.write_text("a,b\n1,2\n", encoding="utf-8")

        ok, result = imp.copy_csv_to_analysis(
            data_dir=tmp_path,
            analytics_targets={},
            bank_label="Santander LikeU (ES)",
            csv_path=src,
            bank_id="santander_likeu",
        )

        assert ok is True
        copied = Path(result)
        assert copied == tmp_path / "santander_likeu" / "firefly_santander_likeu.csv"
        assert copied.exists()

    def test_returns_false_for_missing_source(self, tmp_path):
        """Test that False is returned when source file doesn't exist."""
        ok, msg = imp.copy_csv_to_analysis(
            data_dir=tmp_path,
            analytics_targets={"Bank": ("dir", "file.csv")},
            bank_label="Bank",
            csv_path=tmp_path / "nonexistent.csv",
        )

        assert ok is False
        assert msg == "missing_src"

    def test_returns_false_for_none_path(self, tmp_path):
        """Test that False is returned for None csv_path."""
        ok, msg = imp.copy_csv_to_analysis(
            data_dir=tmp_path,
            analytics_targets={"Bank": ("dir", "file.csv")},
            bank_label="Bank",
            csv_path=None,
        )

        assert ok is False
        assert msg == "missing_src"

    def test_skips_copy_if_source_equals_dest(self, tmp_path):
        """Test that copy is skipped when source and dest are the same."""
        dest_path = tmp_path / "bank" / "firefly.csv"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("data", encoding="utf-8")

        ok, result = imp.copy_csv_to_analysis(
            data_dir=tmp_path,
            analytics_targets={"Bank": ("bank", "firefly.csv")},
            bank_label="Bank",
            csv_path=dest_path,
        )

        assert ok is True
        # Should still succeed, just not copy


# ===========================
# get_csv_last_updated Tests (Additional)
# ===========================

class TestGetCsvLastUpdatedEdgeCases:
    """Test edge cases for get_csv_last_updated."""

    def test_returns_none_for_none_path(self):
        """Test that None is returned for None path."""
        result = imp.get_csv_last_updated(None)
        assert result is None

    def test_returns_none_for_nonexistent_file(self, tmp_path):
        """Test that None is returned for nonexistent file."""
        result = imp.get_csv_last_updated(tmp_path / "nonexistent.csv")
        assert result is None

    def test_returns_formatted_timestamp(self, tmp_path):
        """Test that timestamp is formatted correctly."""
        file_path = tmp_path / "test.csv"
        file_path.write_text("data", encoding="utf-8")

        result = imp.get_csv_last_updated(file_path)

        assert result is not None
        # Should match format YYYY-MM-DD HH:MM:SS
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"
        assert result[16] == ":"
