"""CSRF (Cross-Site Request Forgery) protection middleware.

Provides:
- Double Submit Cookie pattern for CSRF protection
- State parameter validation for OAuth flows
- Exemption for read-only operations (GET, HEAD, OPTIONS)
- Token generation and validation
"""
import hashlib
import hmac
import logging
import secrets
import time
from typing import Callable, Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger(__name__)


# =============================================================================
# CSRF Token Management
# =============================================================================

class CSRFProtection:
    """CSRF token generation and validation.

    Uses HMAC-based tokens with expiration for security.
    """

    def __init__(self, secret_key: str, token_expiry: int = 3600):
        """Initialize CSRF protection.

        Args:
            secret_key: Secret key for HMAC signing
            token_expiry: Token expiration time in seconds (default: 1 hour)
        """
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.token_expiry = token_expiry

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate CSRF token.

        Args:
            session_id: Optional session ID to bind token to

        Returns:
            CSRF token string
        """
        # Generate random token
        random_token = secrets.token_urlsafe(32)

        # Get current timestamp
        timestamp = str(int(time.time()))

        # Create payload: random_token:timestamp:session_id
        payload = f"{random_token}:{timestamp}"
        if session_id:
            payload += f":{session_id}"

        # Create HMAC signature
        signature = hmac.new(
            self.secret_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Return token: signature:payload
        token = f"{signature}:{payload}"

        return token

    def validate_token(
        self,
        token: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Validate CSRF token.

        Args:
            token: CSRF token to validate
            session_id: Optional session ID to verify token binding

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Parse token
            parts = token.split(":")
            if len(parts) < 3:
                logger.warning("CSRF token has invalid format")
                return False

            signature = parts[0]
            random_token = parts[1]
            timestamp = parts[2]
            token_session_id = parts[3] if len(parts) > 3 else None

            # Reconstruct payload
            payload = f"{random_token}:{timestamp}"
            if token_session_id:
                payload += f":{token_session_id}"

            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF token signature verification failed")
                return False

            # Check expiration
            token_time = int(timestamp)
            current_time = int(time.time())

            if current_time - token_time > self.token_expiry:
                logger.warning(
                    f"CSRF token expired (age: {current_time - token_time}s, "
                    f"max: {self.token_expiry}s)"
                )
                return False

            # Verify session binding if provided
            if session_id and token_session_id != session_id:
                logger.warning("CSRF token session ID mismatch")
                return False

            return True

        except Exception as e:
            logger.error(f"CSRF token validation error: {e}", exc_info=True)
            return False


# =============================================================================
# CSRF Middleware
# =============================================================================

class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against CSRF attacks.

    Features:
    - Double Submit Cookie pattern
    - Exempts safe methods (GET, HEAD, OPTIONS)
    - Validates CSRF token in request header or form data
    - Sets CSRF cookie for client
    """

    # Safe methods that don't require CSRF protection
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # Paths exempt from CSRF protection
    EXEMPT_PATHS = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(
        self,
        app,
        secret_key: str,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        token_expiry: int = 3600,
    ):
        """Initialize CSRF middleware.

        Args:
            app: FastAPI application
            secret_key: Secret key for token signing
            cookie_name: Name of CSRF cookie
            header_name: Name of CSRF header
            token_expiry: Token expiration time in seconds
        """
        super().__init__(app)
        self.csrf = CSRFProtection(secret_key, token_expiry)
        self.cookie_name = cookie_name
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and validate CSRF token.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with CSRF cookie

        Raises:
            HTTPException: If CSRF validation fails
        """
        # Check if path is exempt
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Safe methods don't need CSRF protection
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie for future requests
            csrf_token = self.csrf.generate_token()
            response.set_cookie(
                key=self.cookie_name,
                value=csrf_token,
                httponly=True,
                samesite="lax",
                secure=True,  # HTTPS only
            )
            return response

        # Validate CSRF token for state-changing requests
        # Get token from header
        token_from_header = request.headers.get(self.header_name)

        # Get token from cookie
        token_from_cookie = request.cookies.get(self.cookie_name)

        # Both must be present
        if not token_from_header or not token_from_cookie:
            logger.warning(
                f"CSRF validation failed: missing token "
                f"(header={bool(token_from_header)}, cookie={bool(token_from_cookie)})"
            )
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing. Please refresh the page and try again."
            )

        # Tokens must match (Double Submit Cookie pattern)
        if not hmac.compare_digest(token_from_header, token_from_cookie):
            logger.warning("CSRF validation failed: token mismatch")
            raise HTTPException(
                status_code=403,
                detail="CSRF token mismatch. Please refresh the page and try again."
            )

        # Validate token
        if not self.csrf.validate_token(token_from_cookie):
            logger.warning("CSRF validation failed: invalid token")
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired CSRF token. Please refresh the page and try again."
            )

        # Token valid - process request
        response = await call_next(request)

        # Rotate CSRF token on successful request
        new_token = self.csrf.generate_token()
        response.set_cookie(
            key=self.cookie_name,
            value=new_token,
            httponly=True,
            samesite="lax",
            secure=True,
        )

        return response


# =============================================================================
# OAuth State Parameter Validation
# =============================================================================

class OAuthStateProtection:
    """OAuth state parameter generation and validation for CSRF protection.

    Used specifically for OAuth flows (Square, etc.) to prevent CSRF attacks.
    """

    def __init__(self, secret_key: str, state_expiry: int = 600):
        """Initialize OAuth state protection.

        Args:
            secret_key: Secret key for HMAC signing
            state_expiry: State parameter expiration in seconds (default: 10 minutes)
        """
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.state_expiry = state_expiry

    def generate_state(self, vendor_id: str, redirect_uri: Optional[str] = None) -> str:
        """Generate OAuth state parameter.

        Args:
            vendor_id: Vendor ID to bind state to
            redirect_uri: Optional redirect URI to include

        Returns:
            State parameter string
        """
        # Generate random nonce
        nonce = secrets.token_urlsafe(32)

        # Get current timestamp
        timestamp = str(int(time.time()))

        # Create payload: nonce:timestamp:vendor_id[:redirect_uri]
        payload = f"{nonce}:{timestamp}:{vendor_id}"
        if redirect_uri:
            payload += f":{redirect_uri}"

        # Create HMAC signature
        signature = hmac.new(
            self.secret_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Return state: signature:payload (URL-safe)
        state = f"{signature}:{payload}"

        return state

    def validate_state(
        self,
        state: str,
        vendor_id: str,
        redirect_uri: Optional[str] = None
    ) -> bool:
        """Validate OAuth state parameter.

        Args:
            state: State parameter to validate
            vendor_id: Expected vendor ID
            redirect_uri: Expected redirect URI (if originally included)

        Returns:
            True if state is valid, False otherwise
        """
        try:
            # Parse state
            parts = state.split(":")
            if len(parts) < 4:
                logger.warning("OAuth state has invalid format")
                return False

            signature = parts[0]
            nonce = parts[1]
            timestamp = parts[2]
            state_vendor_id = parts[3]
            state_redirect_uri = parts[4] if len(parts) > 4 else None

            # Reconstruct payload
            payload = f"{nonce}:{timestamp}:{state_vendor_id}"
            if state_redirect_uri:
                payload += f":{state_redirect_uri}"

            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("OAuth state signature verification failed")
                return False

            # Check expiration
            state_time = int(timestamp)
            current_time = int(time.time())

            if current_time - state_time > self.state_expiry:
                logger.warning(
                    f"OAuth state expired (age: {current_time - state_time}s, "
                    f"max: {self.state_expiry}s)"
                )
                return False

            # Verify vendor ID
            if state_vendor_id != vendor_id:
                logger.warning("OAuth state vendor ID mismatch")
                return False

            # Verify redirect URI if provided
            if redirect_uri and state_redirect_uri != redirect_uri:
                logger.warning("OAuth state redirect URI mismatch")
                return False

            return True

        except Exception as e:
            logger.error(f"OAuth state validation error: {e}", exc_info=True)
            return False


# =============================================================================
# FastAPI Dependency
# =============================================================================

def get_csrf_token(request: Request) -> str:
    """Get CSRF token from request cookie.

    Args:
        request: FastAPI request

    Returns:
        CSRF token string

    Raises:
        HTTPException: If CSRF token not found

    Usage:
        from fastapi import Depends
        from src.middleware.csrf import get_csrf_token

        @router.post("/items")
        async def create_item(csrf_token: str = Depends(get_csrf_token)):
            # csrf_token is validated automatically
            ...
    """
    token = request.cookies.get("csrf_token")
    if not token:
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing"
        )
    return token


# =============================================================================
# Utility Functions
# =============================================================================

def setup_csrf_protection(app, secret_key: str) -> None:
    """Setup CSRF protection middleware on FastAPI app.

    Args:
        app: FastAPI application
        secret_key: Secret key for CSRF token signing

    Usage:
        from fastapi import FastAPI
        from src.middleware.csrf import setup_csrf_protection
        from src.config import settings

        app = FastAPI()
        setup_csrf_protection(app, settings.secret_key)
    """
    app.add_middleware(
        CSRFMiddleware,
        secret_key=secret_key,
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        token_expiry=3600,  # 1 hour
    )
    logger.info("CSRF protection middleware configured")
