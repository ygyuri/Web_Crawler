"""Custom exception classes."""


class CrawlerError(Exception):
    """Base exception for crawler errors."""

    pass


class HTTPClientError(CrawlerError):
    """Exception for HTTP client errors."""

    pass


class ParsingError(CrawlerError):
    """Exception for HTML parsing errors."""

    pass


class DatabaseError(CrawlerError):
    """Exception for database errors."""

    pass


class ConfigurationError(CrawlerError):
    """Exception for configuration errors."""

    pass

