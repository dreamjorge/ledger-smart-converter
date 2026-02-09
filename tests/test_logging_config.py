"""Tests for logging_config.py utilities."""

import json
import logging
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from logging_config import get_logger, build_run_log, write_json_atomic


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_logger_with_correct_name(self):
        """Test that logger is created with specified name."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_has_stream_handler(self):
        """Test that logger has a StreamHandler attached."""
        logger = get_logger("test_stream")
        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_logger_has_correct_level(self):
        """Test that logger is configured with INFO level."""
        logger = get_logger("test_level")
        assert logger.level == logging.INFO

    def test_logger_propagates(self):
        """Test that logger propagate is enabled (for pytest caplog)."""
        logger = get_logger("test_propagate")
        assert logger.propagate is True

    def test_returns_same_logger_on_second_call(self):
        """Test that calling get_logger twice with same name returns same logger."""
        logger1 = get_logger("test_same")
        logger2 = get_logger("test_same")
        assert logger1 is logger2

    def test_does_not_add_duplicate_handlers(self):
        """Test that calling get_logger multiple times doesn't add duplicate handlers."""
        logger = get_logger("test_no_dup")
        initial_handler_count = len(logger.handlers)

        # Call again
        logger = get_logger("test_no_dup")
        assert len(logger.handlers) == initial_handler_count

    def test_default_name_is_importer(self):
        """Test that default logger name is 'importer'."""
        logger = get_logger()
        assert logger.name == "importer"


class TestBuildRunLog:
    """Test build_run_log function."""

    def test_creates_log_with_required_fields(self):
        """Test that log dictionary contains all required fields."""
        log = build_run_log(
            bank_id="santander",
            input_count=100,
            output_count=95,
            warning_count=5
        )

        assert "timestamp_utc" in log
        assert log["bank_id"] == "santander"
        assert log["input_count"] == 100
        assert log["output_count"] == 95
        assert log["warning_count"] == 5
        assert "metadata" in log

    def test_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO format."""
        log = build_run_log("test", 0, 0, 0)
        timestamp = log["timestamp_utc"]

        # Should be parseable as ISO format datetime
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_timestamp_is_utc(self):
        """Test that timestamp is in UTC timezone."""
        with patch('logging_config.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.isoformat.return_value = "2026-01-15T10:30:00+00:00"
            mock_datetime.now.return_value = mock_now

            log = build_run_log("test", 0, 0, 0)

            # Verify datetime.now was called with timezone.utc
            mock_datetime.now.assert_called_once_with(timezone.utc)
            assert "timestamp_utc" in log

    def test_includes_optional_metadata(self):
        """Test that optional metadata is included."""
        metadata = {"source_file": "test.pdf", "pages": 5}
        log = build_run_log("hsbc", 50, 48, 2, metadata=metadata)

        assert log["metadata"]["source_file"] == "test.pdf"
        assert log["metadata"]["pages"] == 5

    def test_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict when not provided."""
        log = build_run_log("test", 0, 0, 0)
        assert log["metadata"] == {}

    def test_handles_none_metadata(self):
        """Test that None metadata is converted to empty dict."""
        log = build_run_log("test", 0, 0, 0, metadata=None)
        assert log["metadata"] == {}

    def test_handles_zero_counts(self):
        """Test handling of zero counts."""
        log = build_run_log("test", 0, 0, 0)
        assert log["input_count"] == 0
        assert log["output_count"] == 0
        assert log["warning_count"] == 0


class TestWriteJsonAtomic:
    """Test write_json_atomic function."""

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        nested_path = tmp_path / "level1" / "level2" / "test.json"
        payload = {"test": "data"}

        write_json_atomic(nested_path, payload)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_writes_valid_json(self, tmp_path):
        """Test that valid JSON is written to file."""
        file_path = tmp_path / "test.json"
        payload = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "data"}
        }

        write_json_atomic(file_path, payload)

        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == payload

    def test_handles_unicode_characters(self, tmp_path):
        """Test that Unicode characters are preserved."""
        file_path = tmp_path / "unicode.json"
        payload = {
            "spanish": "Niño",
            "japanese": "日本語",
            "emoji": "🎉",
            "special": "Crédito"
        }

        write_json_atomic(file_path, payload)

        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["spanish"] == "Niño"
        assert loaded["japanese"] == "日本語"
        assert loaded["emoji"] == "🎉"

    def test_overwrites_existing_file(self, tmp_path):
        """Test that existing file is overwritten."""
        file_path = tmp_path / "overwrite.json"

        # Write initial data
        write_json_atomic(file_path, {"version": 1})

        # Overwrite with new data
        write_json_atomic(file_path, {"version": 2})

        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["version"] == 2

    def test_json_is_formatted_with_indent(self, tmp_path):
        """Test that JSON is formatted with indentation."""
        file_path = tmp_path / "formatted.json"
        payload = {"key1": "value1", "key2": {"nested": "value2"}}

        write_json_atomic(file_path, payload)

        content = file_path.read_text(encoding="utf-8")

        # Indented JSON should have newlines
        assert "\n" in content
        # Should have 2-space indentation
        assert "  " in content

    def test_uses_atomic_write_pattern(self, tmp_path):
        """Test that write uses atomic pattern (write to temp, then rename)."""
        file_path = tmp_path / "atomic.json"
        payload = {"atomic": "test"}

        with patch.object(Path, 'write_text') as mock_write:
            with patch.object(Path, 'replace') as mock_replace:
                write_json_atomic(file_path, payload)

                # Should write to temp file first
                assert mock_write.called
                # Should rename temp to final
                assert mock_replace.called

    def test_temp_file_is_cleaned_up(self, tmp_path):
        """Test that temporary file is not left behind."""
        file_path = tmp_path / "cleanup.json"
        payload = {"test": "data"}

        write_json_atomic(file_path, payload)

        # Final file should exist
        assert file_path.exists()

        # Temp file should not exist
        temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
        assert not temp_file.exists()

    def test_handles_empty_dict(self, tmp_path):
        """Test writing empty dictionary."""
        file_path = tmp_path / "empty.json"
        write_json_atomic(file_path, {})

        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == {}
