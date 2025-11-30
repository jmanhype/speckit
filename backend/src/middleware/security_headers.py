"""Security headers middleware for production hardening.

Implements OWASP recommended security headers:
- X-Frame-Options (clickjacking protection)
- X-Content-Type-Options (MIME sniffing protection)
- X-XSS-Protection (XSS protection)
- Strict-Transport-Security (HTTPS enforcement)
- Content-Security-Policy (CSP)
- Referrer-Policy (referrer leakage protection)
- Permissions-Policy (feature control)
"""
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config import settings


logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app: ASGIApp, enable_strict_csp: bool = False):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
            enable_strict_csp: Whether to enable strict CSP (may break some features)
        """
        super().__init__(app)
        self.enable_strict_csp = enable_strict_csp
        self.is_production = settings.environment == 'production'

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # X-Frame-Options: Prevent clickjacking
        # DENY = Cannot be displayed in frame/iframe
        # SAMEORIGIN = Can be framed by same origin only
        response.headers['X-Frame-Options'] = 'DENY'

        # X-Content-Type-Options: Prevent MIME sniffing
        # nosniff = Browser should not try to guess content type
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # X-XSS-Protection: Enable browser XSS filter
        # 1; mode=block = Enable XSS filter, block page if attack detected
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Strict-Transport-Security (HSTS): Enforce HTTPS
        # Only add in production with HTTPS
        if self.is_production:
            # max-age=31536000 = 1 year
            # includeSubDomains = Apply to all subdomains
            # preload = Allow browser preload list inclusion
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # Content-Security-Policy (CSP): Control resource loading
        if self.enable_strict_csp:
            # Strict CSP - may break some features
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # Moderate CSP - allows more flexibility
            csp = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https:; "
                "frame-ancestors 'none'"
            )
        response.headers['Content-Security-Policy'] = csp

        # Referrer-Policy: Control referrer information
        # strict-origin-when-cross-origin = Send origin only on cross-origin requests
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions-Policy: Control browser features
        # Disable potentially dangerous features
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )

        # X-Permitted-Cross-Domain-Policies: Control Adobe Flash/PDF
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'

        # X-Download-Options: Prevent IE from executing downloads in site context
        response.headers['X-Download-Options'] = 'noopen'

        # Remove server header (information disclosure)
        if 'Server' in response.headers:
            del response.headers['Server']

        # Remove X-Powered-By header (information disclosure)
        if 'X-Powered-By' in response.headers:
            del response.headers['X-Powered-By']

        return response
