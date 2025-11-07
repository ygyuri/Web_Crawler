"""Centralized logging configuration."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Log format (json, text)
    """
    # Use settings defaults if not provided
    log_level = log_level or settings.logging.level
    log_file = log_file or settings.logging.file
    log_format = log_format or settings.logging.format

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # File handler (if log file specified)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when=settings.logging.file_rotation,
            interval=1,
            backupCount=settings.logging.file_retention,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)

    # Formatter
    if log_format == "json":
        # Use structured JSON logging
        import json
        from datetime import datetime

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                # Add exception info if present
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                # Add extra fields
                if hasattr(record, "extra_fields"):
                    log_data.update(record.extra_fields)
                return json.dumps(log_data)

        formatter = JSONFormatter()
    else:
        # Standard text formatter
        if settings.logging.include_timestamp:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
            )
        else:
            format_string = (
                "%(name)s - %(levelname)s - "
                "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
            )
        formatter = logging.Formatter(format_string)

    # Apply formatter to all handlers
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Set levels for third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import
setup_logging()

