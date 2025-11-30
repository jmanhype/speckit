"""Input validation and sanitization utilities.

Provides defense-in-depth against:
- SQL injection (complement to SQLAlchemy's parameterized queries)
- XSS (Cross-Site Scripting)
- Path traversal
- Command injection
- HTML injection
"""
import re
import html
import logging
from typing import Optional, List
from pathlib import Path


logger = logging.getLogger(__name__)


class InputValidator:
    """Utilities for validating and sanitizing user input."""

    # Patterns for detection
    SQL_INJECTION_PATTERN = re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
        re.IGNORECASE
    )

    XSS_PATTERN = re.compile(
        r"(<script|javascript:|onerror=|onload=|<iframe|<object|<embed)",
        re.IGNORECASE
    )

    PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\")

    # Allowed characters for different field types
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    @classmethod
    def sanitize_html(cls, text: str, max_length: Optional[int] = None) -> str:
        """Sanitize HTML input to prevent XSS.

        Args:
            text: Input text
            max_length: Maximum allowed length

        Returns:
            Sanitized text with HTML entities escaped

        Example:
            >>> InputValidator.sanitize_html("<script>alert('xss')</script>")
            "&lt;script&gt;alert('xss')&lt;/script&gt;"
        """
        if not text:
            return ""

        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length]

        # Escape HTML entities
        sanitized = html.escape(text, quote=True)

        return sanitized

    @classmethod
    def validate_no_sql_injection(cls, text: str) -> bool:
        """Check if text contains potential SQL injection patterns.

        Note: This is defense-in-depth. SQLAlchemy's parameterized queries
        are the primary defense against SQL injection.

        Args:
            text: Input text to check

        Returns:
            True if safe, False if suspicious patterns detected
        """
        if not text:
            return True

        # Check for SQL keywords (basic heuristic)
        if cls.SQL_INJECTION_PATTERN.search(text):
            logger.warning(
                f"Potential SQL injection attempt detected",
                extra={'input_sample': text[:100]}
            )
            return False

        return True

    @classmethod
    def validate_no_xss(cls, text: str) -> bool:
        """Check if text contains potential XSS patterns.

        Args:
            text: Input text to check

        Returns:
            True if safe, False if suspicious patterns detected
        """
        if not text:
            return True

        if cls.XSS_PATTERN.search(text):
            logger.warning(
                f"Potential XSS attempt detected",
                extra={'input_sample': text[:100]}
            )
            return False

        return True

    @classmethod
    def validate_no_path_traversal(cls, path: str) -> bool:
        """Check if path contains path traversal attempts.

        Args:
            path: File path to check

        Returns:
            True if safe, False if traversal detected
        """
        if not path:
            return True

        if cls.PATH_TRAVERSAL_PATTERN.search(path):
            logger.warning(
                f"Path traversal attempt detected: {path}",
                extra={'path': path}
            )
            return False

        return True

    @classmethod
    def validate_alphanumeric(cls, text: str, allow_dash: bool = True) -> bool:
        """Validate that text contains only alphanumeric characters.

        Args:
            text: Input text
            allow_dash: Whether to allow dash and underscore

        Returns:
            True if valid, False otherwise
        """
        if not text:
            return False

        if allow_dash:
            return bool(cls.ALPHANUMERIC_PATTERN.match(text))
        else:
            return text.isalnum()

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid format, False otherwise
        """
        if not email:
            return False

        # Basic regex check
        if not cls.EMAIL_PATTERN.match(email):
            return False

        # Additional checks
        if len(email) > 254:  # RFC 5321
            return False

        local, domain = email.rsplit('@', 1)
        if len(local) > 64:  # RFC 5321
            return False

        return True

    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format.

        Args:
            uuid_str: UUID string to validate

        Returns:
            True if valid UUID format, False otherwise
        """
        if not uuid_str:
            return False

        return bool(cls.UUID_PATTERN.match(uuid_str))

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and special characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem
        """
        if not filename:
            return "unnamed"

        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove leading/trailing whitespace and dots
        filename = filename.strip('. ')

        # Replace problematic characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)

        # Limit length (most filesystems support 255)
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            name = name[:255 - len(ext) - 1]
            filename = f"{name}.{ext}" if ext else name

        return filename or "unnamed"

    @classmethod
    def validate_safe_path(cls, path: str, base_dir: str) -> bool:
        """Validate that a path is within a base directory.

        Prevents path traversal attacks.

        Args:
            path: Path to validate
            base_dir: Base directory that path must be within

        Returns:
            True if path is safe (within base_dir), False otherwise
        """
        try:
            # Resolve to absolute paths
            base_path = Path(base_dir).resolve()
            file_path = Path(path).resolve()

            # Check if file_path is within base_path
            return base_path in file_path.parents or base_path == file_path

        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False

    @classmethod
    def sanitize_search_query(cls, query: str, max_length: int = 200) -> str:
        """Sanitize search query input.

        Args:
            query: Search query string
            max_length: Maximum allowed length

        Returns:
            Sanitized query string
        """
        if not query:
            return ""

        # Truncate
        query = query[:max_length]

        # Remove control characters
        query = ''.join(char for char in query if ord(char) >= 32 or char in '\n\r\t')

        # Strip whitespace
        query = query.strip()

        return query

    @classmethod
    def validate_json_keys(cls, data: dict, allowed_keys: List[str]) -> bool:
        """Validate that JSON object only contains allowed keys.

        Prevents injection of unexpected fields.

        Args:
            data: Dictionary to validate
            allowed_keys: List of allowed key names

        Returns:
            True if all keys are allowed, False otherwise
        """
        if not isinstance(data, dict):
            return False

        actual_keys = set(data.keys())
        allowed_set = set(allowed_keys)

        unexpected_keys = actual_keys - allowed_set

        if unexpected_keys:
            logger.warning(
                f"Unexpected JSON keys detected: {unexpected_keys}",
                extra={'unexpected_keys': list(unexpected_keys)}
            )
            return False

        return True


# Convenience functions
def sanitize_html(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize HTML input (convenience wrapper)."""
    return InputValidator.sanitize_html(text, max_length)


def validate_email(email: str) -> bool:
    """Validate email format (convenience wrapper)."""
    return InputValidator.validate_email(email)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename (convenience wrapper)."""
    return InputValidator.sanitize_filename(filename)
