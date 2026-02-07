class ImporterError(Exception):
    """Base error for importer failures."""


class ConfigError(ImporterError):
    """Invalid or missing configuration."""


class ParseError(ImporterError):
    """Input parsing failure."""


class ValidationError(ImporterError):
    """Record validation failure."""
