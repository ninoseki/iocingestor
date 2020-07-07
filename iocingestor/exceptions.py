class IngestorError(Exception):
    """Base exception class."""


class DependencyError(IngestorError):
    """Missing dependency."""


class PluginError(IngestorError):
    """Missing plugin."""
