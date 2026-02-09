"""Tests for custom exception classes in errors.py"""

import pytest
from errors import ImporterError, ConfigError, ParseError, ValidationError


class TestExceptionHierarchy:
    """Test that custom exceptions have proper inheritance."""

    def test_importer_error_is_base_exception(self):
        """ImporterError should inherit from Exception."""
        assert issubclass(ImporterError, Exception)

    def test_config_error_inherits_from_importer_error(self):
        """ConfigError should inherit from ImporterError."""
        assert issubclass(ConfigError, ImporterError)
        assert issubclass(ConfigError, Exception)

    def test_parse_error_inherits_from_importer_error(self):
        """ParseError should inherit from ImporterError."""
        assert issubclass(ParseError, ImporterError)
        assert issubclass(ParseError, Exception)

    def test_validation_error_inherits_from_importer_error(self):
        """ValidationError should inherit from ImporterError."""
        assert issubclass(ValidationError, ImporterError)
        assert issubclass(ValidationError, Exception)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught properly."""

    def test_can_raise_and_catch_importer_error(self):
        """Test raising and catching ImporterError."""
        with pytest.raises(ImporterError) as exc_info:
            raise ImporterError("Test error")
        assert str(exc_info.value) == "Test error"

    def test_can_raise_and_catch_config_error(self):
        """Test raising and catching ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            raise ConfigError("Invalid config")
        assert str(exc_info.value) == "Invalid config"

    def test_can_raise_and_catch_parse_error(self):
        """Test raising and catching ParseError."""
        with pytest.raises(ParseError) as exc_info:
            raise ParseError("Parsing failed")
        assert str(exc_info.value) == "Parsing failed"

    def test_can_raise_and_catch_validation_error(self):
        """Test raising and catching ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Validation failed")
        assert str(exc_info.value) == "Validation failed"

    def test_config_error_caught_as_importer_error(self):
        """ConfigError should be catchable as ImporterError."""
        with pytest.raises(ImporterError):
            raise ConfigError("Config issue")

    def test_parse_error_caught_as_importer_error(self):
        """ParseError should be catchable as ImporterError."""
        with pytest.raises(ImporterError):
            raise ParseError("Parse issue")

    def test_validation_error_caught_as_importer_error(self):
        """ValidationError should be catchable as ImporterError."""
        with pytest.raises(ImporterError):
            raise ValidationError("Validation issue")


class TestExceptionMessages:
    """Test that exceptions preserve custom messages."""

    def test_importer_error_with_custom_message(self):
        """ImporterError should preserve custom messages."""
        msg = "Critical importer failure: missing file"
        with pytest.raises(ImporterError, match=msg):
            raise ImporterError(msg)

    def test_config_error_with_multiline_message(self):
        """ConfigError should handle multiline messages."""
        msg = "Config error:\n- Missing field 'name'\n- Invalid value for 'closing_day'"
        try:
            raise ConfigError(msg)
        except ConfigError as e:
            assert str(e) == msg

    def test_exception_without_message(self):
        """Exceptions should work without messages."""
        with pytest.raises(ParseError):
            raise ParseError()
