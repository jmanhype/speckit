"""Structured logging configuration for production.

Features:
- JSON structured logging for production
- Human-readable logging for development
- Correlation ID tracking
- Request/response logging
- Error tracking with stack traces
- Log aggregation support (Datadog, CloudWatch, etc.)
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger

from src.config import settings


class StructuredFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with additional context fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record.

        Args:
            log_record: The log record dictionary to modify
            record: The original LogRecord
            message_dict: Additional message data
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add standard fields
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Add environment
        log_record['environment'] = settings.environment

        # Add correlation_id if present in extra
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id

        # Add vendor_id if present
        if hasattr(record, 'vendor_id'):
            log_record['vendor_id'] = str(record.vendor_id)

        # Add request info if present
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'request_method'):
            log_record['request_method'] = record.request_method
        if hasattr(record, 'request_path'):
            log_record['request_path'] = record.request_path
        if hasattr(record, 'request_ip'):
            log_record['request_ip'] = record.request_ip

        # Add error details if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
            }


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    # Color codes for terminal output
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
            record: The log record to format

        Returns:
            Formatted log string
        """
        # Get color for level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Build log message
        parts = [
            f"{color}{record.levelname:<8}{reset}",
            f"{timestamp}",
            f"{record.name}:{record.funcName}:{record.lineno}",
            f"{record.getMessage()}",
        ]

        # Add correlation_id if present
        if hasattr(record, 'correlation_id'):
            parts.insert(3, f"[{record.correlation_id}]")

        log_line = " | ".join(parts)

        # Add exception info if present
        if record.exc_info:
            log_line += '\n' + self.formatException(record.exc_info)

        return log_line


def setup_logging() -> None:
    """Configure application logging.

    Sets up:
    - JSON structured logging for production
    - Human-readable logging for development
    - Log levels based on environment
    - Multiple handlers (console, file)
    """
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on environment
    if settings.environment == 'production':
        # Use JSON formatter for production
        formatter = StructuredFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Use human-readable formatter for development
        formatter = HumanReadableFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler for errors (optional)
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(StructuredFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        ))
        root_logger.addHandler(file_handler)

    # Set log levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('alembic').setLevel(logging.INFO)

    logging.info(
        f"Logging configured: level={log_level}, environment={settings.environment}"
    )


class LogContext:
    """Context manager for adding extra fields to log records."""

    def __init__(self, **kwargs):
        """Initialize log context with extra fields.

        Args:
            **kwargs: Extra fields to add to log records
        """
        self.extra = kwargs
        self._old_factory = None

    def __enter__(self):
        """Enter context and modify log record factory."""
        self._old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            for key, value in self.extra.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)


def get_logger(name: str, **extra) -> logging.Logger:
    """Get a logger with optional extra context.

    Args:
        name: Logger name (usually __name__)
        **extra: Extra fields to include in all log records

    Returns:
        Logger instance

    Usage:
        logger = get_logger(__name__, service='api')
        logger.info("Request received", extra={'request_id': req_id})
    """
    logger = logging.getLogger(name)

    if extra:
        # Wrap logger to add extra fields
        class LoggerAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                # Merge extra fields
                if 'extra' not in kwargs:
                    kwargs['extra'] = {}
                kwargs['extra'].update(self.extra)
                return msg, kwargs

        return LoggerAdapter(logger, extra)

    return logger
