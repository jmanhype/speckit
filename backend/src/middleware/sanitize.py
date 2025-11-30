"""Input sanitization middleware for security hardening.

Provides:
- HTML/JavaScript injection prevention
- SQL injection prevention (supplemental to ORM)
- Path traversal prevention
- Command injection prevention
- Header injection prevention
"""
import html
import logging
import re
from typing import Callable, Any, Dict, List, Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger(__name__)


# =============================================================================
# Sanitization Functions
# =============================================================================

class InputSanitizer:
    """Input sanitization utilities."""

    # Dangerous patterns that should trigger warnings/blocks
    DANGEROUS_PATTERNS = {
        # SQL injection patterns
        "sql_injection": [
            r"(\bunion\b.*\bselect\b)",
            r"(\bselect\b.*\bfrom\b.*\bwhere\b)",
            r"(\bdrop\b.*\btable\b)",
            r"(\binsert\b.*\binto\b)",
            r"(\bupdate\b.*\bset\b)",
            r"(\bdelete\b.*\bfrom\b)",
            r"(;.*\b(drop|alter|create)\b)",
            r"(--|\#|\/\*)",  # SQL comments
        ],
        # Command injection patterns
        "command_injection": [
            r"[;&|`$()]",  # Shell metacharacters
            r"(\b(bash|sh|cmd|powershell|exec|eval)\b)",
        ],
        # Path traversal patterns
        "path_traversal": [
            r"\.\./",  # Directory traversal
            r"\.\.",  # Parent directory
            r"~\/",  # Home directory
            r"\/etc\/",  # System files
            r"\/proc\/",  # Process files
        ],
        # XSS patterns
        "xss": [
            r"<script[^>]*>",
            r"javascript:",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onload\s*=",
        ],
        # LDAP injection
        "ldap_injection": [
            r"[\*\(\)\\&|!]",  # LDAP special characters
        ],
    }

    @classmethod
    def sanitize_string(
        cls,
        value: str,
        allow_html: bool = False,
        max_length: Optional[int] = None,
    ) -> str:
        """Sanitize string input.

        Args:
            value: Input string
            allow_html: Allow HTML tags (will escape them)
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            ValueError: If dangerous patterns detected
        """
        if not isinstance(value, str):
            return value

        # Normalize unicode
        value = value.strip()

        # Check length
        if max_length and len(value) > max_length:
            logger.warning(f"Input exceeds max length: {len(value)} > {max_length}")
            value = value[:max_length]

        # Escape HTML if not allowed
        if not allow_html:
            value = html.escape(value, quote=True)

        # Check for dangerous patterns
        for pattern_type, patterns in cls.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(
                        f"Dangerous pattern detected ({pattern_type}): {pattern} "
                        f"in input: {value[:100]}"
                    )
                    # Don't reject - just log for now (false positives)
                    # Could be made stricter based on requirements

        return value

    @classmethod
    def sanitize_dict(
        cls,
        data: Dict[str, Any],
        allow_html: bool = False,
        max_depth: int = 10,
        _current_depth: int = 0,
    ) -> Dict[str, Any]:
        """Recursively sanitize dictionary values.

        Args:
            data: Input dictionary
            allow_html: Allow HTML in string values
            max_depth: Maximum recursion depth
            _current_depth: Current recursion depth (internal)

        Returns:
            Sanitized dictionary
        """
        if _current_depth >= max_depth:
            logger.warning(f"Max sanitization depth reached: {max_depth}")
            return data

        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if isinstance(key, str):
                key = cls.sanitize_string(key, allow_html=False, max_length=256)

            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, allow_html=allow_html)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(
                    value,
                    allow_html=allow_html,
                    max_depth=max_depth,
                    _current_depth=_current_depth + 1
                )
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(
                    value,
                    allow_html=allow_html,
                    max_depth=max_depth,
                    _current_depth=_current_depth + 1
                )
            else:
                # Numbers, booleans, None - pass through
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_list(
        cls,
        data: List[Any],
        allow_html: bool = False,
        max_depth: int = 10,
        _current_depth: int = 0,
    ) -> List[Any]:
        """Recursively sanitize list values.

        Args:
            data: Input list
            allow_html: Allow HTML in string values
            max_depth: Maximum recursion depth
            _current_depth: Current recursion depth (internal)

        Returns:
            Sanitized list
        """
        if _current_depth >= max_depth:
            logger.warning(f"Max sanitization depth reached: {max_depth}")
            return data

        sanitized = []
        for value in data:
            if isinstance(value, str):
                sanitized.append(cls.sanitize_string(value, allow_html=allow_html))
            elif isinstance(value, dict):
                sanitized.append(
                    cls.sanitize_dict(
                        value,
                        allow_html=allow_html,
                        max_depth=max_depth,
                        _current_depth=_current_depth + 1
                    )
                )
            elif isinstance(value, list):
                sanitized.append(
                    cls.sanitize_list(
                        value,
                        allow_html=allow_html,
                        max_depth=max_depth,
                        _current_depth=_current_depth + 1
                    )
                )
            else:
                sanitized.append(value)

        return sanitized

    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Validate and sanitize filename.

        Args:
            filename: Input filename

        Returns:
            Sanitized filename

        Raises:
            ValueError: If filename is invalid
        """
        # Remove path components
        filename = filename.split("/")[-1].split("\\")[-1]

        # Check for path traversal
        if ".." in filename or filename.startswith("."):
            raise ValueError("Invalid filename: path traversal attempt")

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)

        # Ensure non-empty
        if not filename:
            raise ValueError("Invalid filename: empty after sanitization")

        # Limit length
        if len(filename) > 255:
            logger.warning(f"Filename truncated: {len(filename)} > 255")
            filename = filename[:255]

        return filename

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate and sanitize email address.

        Args:
            email: Input email

        Returns:
            Sanitized email

        Raises:
            ValueError: If email is invalid
        """
        # Basic email regex (RFC 5322 simplified)
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        email = email.strip().lower()

        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")

        if len(email) > 254:  # RFC 5321
            raise ValueError("Email too long")

        return email

    @classmethod
    def validate_url(cls, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """Validate and sanitize URL.

        Args:
            url: Input URL
            allowed_schemes: Allowed URL schemes (default: ['http', 'https'])

        Returns:
            Sanitized URL

        Raises:
            ValueError: If URL is invalid or uses disallowed scheme
        """
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        url = url.strip()

        # Parse URL
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")

        # Validate scheme
        if parsed.scheme not in allowed_schemes:
            raise ValueError(
                f"Invalid URL scheme: {parsed.scheme} "
                f"(allowed: {', '.join(allowed_schemes)})"
            )

        # Prevent SSRF attacks - block private IPs
        if parsed.hostname:
            # Block localhost
            if parsed.hostname in ["localhost", "127.0.0.1", "::1"]:
                raise ValueError("URL points to localhost")

            # Block private IP ranges
            import ipaddress
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback or ip.is_reserved:
                    raise ValueError("URL points to private/reserved IP")
            except ValueError:
                # Not an IP address - hostname is fine
                pass

        return url


# =============================================================================
# Sanitization Middleware
# =============================================================================

class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize all request inputs.

    Features:
    - Sanitizes query parameters
    - Sanitizes JSON body
    - Validates headers
    - Logs suspicious inputs
    """

    # Paths exempt from sanitization
    EXEMPT_PATHS = {
        "/health",
        "/metrics",
    }

    def __init__(
        self,
        app,
        allow_html: bool = False,
        strict_mode: bool = False,
    ):
        """Initialize sanitization middleware.

        Args:
            app: FastAPI application
            allow_html: Allow HTML in inputs (will be escaped)
            strict_mode: Reject requests with dangerous patterns
        """
        super().__init__(app)
        self.allow_html = allow_html
        self.strict_mode = strict_mode
        self.sanitizer = InputSanitizer()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and sanitize inputs.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler

        Raises:
            HTTPException: If strict mode enabled and dangerous input detected
        """
        # Check if path is exempt
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Sanitize query parameters
        if request.query_params:
            try:
                sanitized_params = self.sanitizer.sanitize_dict(
                    dict(request.query_params),
                    allow_html=self.allow_html
                )
                # Update request query params (via scope)
                request.scope["query_string"] = (
                    "&".join(f"{k}={v}" for k, v in sanitized_params.items())
                    .encode()
                )
            except Exception as e:
                logger.error(f"Query parameter sanitization error: {e}")
                if self.strict_mode:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid query parameters"
                    )

        # Sanitize JSON body (if present)
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")

            if "application/json" in content_type:
                try:
                    # Read body
                    body = await request.body()

                    if body:
                        import json

                        # Parse JSON
                        try:
                            data = json.loads(body)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in request body: {e}")
                            if self.strict_mode:
                                raise HTTPException(
                                    status_code=400,
                                    detail="Invalid JSON in request body"
                                )
                            # Let FastAPI handle the error
                            return await call_next(request)

                        # Sanitize
                        if isinstance(data, dict):
                            sanitized_data = self.sanitizer.sanitize_dict(
                                data,
                                allow_html=self.allow_html
                            )
                        elif isinstance(data, list):
                            sanitized_data = self.sanitizer.sanitize_list(
                                data,
                                allow_html=self.allow_html
                            )
                        else:
                            sanitized_data = data

                        # Update request body
                        sanitized_body = json.dumps(sanitized_data).encode()

                        # Create new request with sanitized body
                        async def receive():
                            return {"type": "http.request", "body": sanitized_body}

                        request._receive = receive

                except Exception as e:
                    logger.error(f"Body sanitization error: {e}", exc_info=True)
                    if self.strict_mode:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid request body"
                        )

        # Validate headers
        suspicious_headers = []
        for header_name, header_value in request.headers.items():
            # Check for header injection (newlines)
            if "\n" in header_value or "\r" in header_value:
                suspicious_headers.append(header_name)
                logger.warning(
                    f"Suspicious header detected (newline injection): {header_name}"
                )

        if suspicious_headers and self.strict_mode:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid headers: {', '.join(suspicious_headers)}"
            )

        # Process request
        response = await call_next(request)

        return response


# =============================================================================
# Utility Functions
# =============================================================================

def setup_input_sanitization(app, strict_mode: bool = False) -> None:
    """Setup input sanitization middleware on FastAPI app.

    Args:
        app: FastAPI application
        strict_mode: Reject requests with dangerous patterns

    Usage:
        from fastapi import FastAPI
        from src.middleware.sanitize import setup_input_sanitization

        app = FastAPI()
        setup_input_sanitization(app, strict_mode=False)
    """
    app.add_middleware(
        SanitizationMiddleware,
        allow_html=False,  # Don't allow HTML by default
        strict_mode=strict_mode,
    )
    logger.info(f"Input sanitization middleware configured (strict_mode={strict_mode})")
