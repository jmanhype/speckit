"""
Audit trail middleware

Automatically logs all API requests for compliance and security.
"""

import json
import time
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import UploadFile

from src.database import SessionLocal
from src.models.audit_log import AuditAction
from src.services.audit_service import AuditService
from src.logging_config import get_logger

logger = get_logger(__name__)


class AuditTrailMiddleware(BaseHTTPMiddleware):
    """
    Middleware to audit all API requests

    Records:
    - Request method, path, params
    - Response status code
    - User information (if authenticated)
    - Timestamp and duration
    - IP address and user agent

    Exemptions:
    - Health check endpoints
    - Static assets
    - Options requests (CORS preflight)
    """

    # Endpoints to skip auditing
    SKIP_PATHS = {
        "/health",
        "/health/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/metrics",  # Prometheus metrics
    }

    # Methods that don't modify data (generally don't need detailed auditing)
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and log audit trail

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip audit logging for certain paths
        if self._should_skip_audit(request):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Get vendor_id if authenticated (set by auth middleware)
        vendor_id = getattr(request.state, "vendor_id", None)
        user_email = getattr(request.state, "user_email", None)

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log audit trail (async to not block response)
        try:
            self._log_request(
                request=request,
                response=response,
                vendor_id=vendor_id,
                user_email=user_email,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"Error logging audit trail: {e}", exc_info=True)

        return response

    def _should_skip_audit(self, request: Request) -> bool:
        """
        Determine if request should be skipped for auditing

        Args:
            request: FastAPI request

        Returns:
            True if should skip, False otherwise
        """
        # Skip health checks and static assets
        if request.url.path in self.SKIP_PATHS:
            return True

        # Skip paths starting with exempted prefixes
        if request.url.path.startswith("/static/"):
            return True

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True

        return False

    def _log_request(
        self,
        request: Request,
        response: Response,
        vendor_id: str | None,
        user_email: str | None,
        duration_ms: float,
    ) -> None:
        """
        Log request to audit trail

        Args:
            request: FastAPI request
            response: Response
            vendor_id: Vendor ID (if authenticated)
            user_email: User email (if authenticated)
            duration_ms: Request duration in milliseconds
        """
        # Create database session
        db = SessionLocal()
        try:
            audit_service = AuditService(db)

            # Determine action based on method and path
            action = self._determine_action(request)

            # Extract resource info from path
            resource_type, resource_id = self._extract_resource_info(request)

            # Get request data (for POST/PUT/PATCH)
            request_data = self._get_request_data(request)

            # Determine if request contains sensitive data
            is_sensitive = self._is_sensitive_endpoint(request.url.path)

            # Build changes summary
            changes_summary = (
                f"{request.method} {request.url.path} - "
                f"{response.status_code} ({duration_ms:.0f}ms)"
            )

            # Log the action
            audit_service.log_action(
                vendor_id=vendor_id or "unauthenticated",
                action=action,
                user_id=vendor_id,  # For vendors, user_id = vendor_id
                user_email=user_email,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=None,  # Not tracked at middleware level
                new_values=request_data if request.method in {"POST", "PUT", "PATCH"} else None,
                changes_summary=changes_summary,
                request=request,
                is_sensitive=is_sensitive,
            )

            logger.debug(
                f"Audit trail logged: {action} on {resource_type}:{resource_id}",
                extra={
                    "vendor_id": vendor_id,
                    "action": action,
                    "resource_type": resource_type,
                    "duration_ms": duration_ms,
                },
            )

        except Exception as e:
            logger.error(f"Failed to log audit trail: {e}", exc_info=True)
        finally:
            db.close()

    def _determine_action(self, request: Request) -> str:
        """
        Determine audit action from request

        Args:
            request: FastAPI request

        Returns:
            Action string (from AuditAction enum)
        """
        method = request.method
        path = request.url.path.lower()

        # Authentication actions
        if "/auth/" in path:
            if "login" in path:
                return AuditAction.LOGIN
            if "logout" in path:
                return AuditAction.LOGOUT
            if "register" in path:
                return AuditAction.ACCOUNT_CREATED
            return AuditAction.OTHER

        # GDPR actions
        if "data-export" in path:
            return AuditAction.DATA_EXPORTED
        if "/vendors/me" in path and method == "DELETE":
            return AuditAction.ACCOUNT_DELETED

        # CRUD operations
        if method == "POST":
            return AuditAction.CREATE
        elif method in {"PUT", "PATCH"}:
            return AuditAction.UPDATE
        elif method == "DELETE":
            return AuditAction.DELETE
        elif method == "GET":
            # Distinguish between list and view
            if resource_id := self._extract_resource_info(request)[1]:
                return AuditAction.VIEW
            return AuditAction.LIST
        else:
            return AuditAction.OTHER

    def _extract_resource_info(self, request: Request) -> tuple[str | None, str | None]:
        """
        Extract resource type and ID from request path

        Args:
            request: FastAPI request

        Returns:
            Tuple of (resource_type, resource_id)
        """
        path_parts = request.url.path.strip("/").split("/")

        # Skip "api" and version prefixes
        if path_parts and path_parts[0] == "api":
            path_parts = path_parts[1:]
        if path_parts and path_parts[0].startswith("v"):
            path_parts = path_parts[1:]

        # First part is usually resource type
        resource_type = path_parts[0] if path_parts else None

        # Look for UUID-like IDs (36 chars with dashes)
        resource_id = None
        for part in path_parts:
            if len(part) == 36 and part.count("-") >= 4:  # Likely a UUID
                resource_id = part
                break

        return resource_type, resource_id

    def _get_request_data(self, request: Request) -> dict | None:
        """
        Extract request data (sanitized)

        Args:
            request: FastAPI request

        Returns:
            Request data dictionary (sanitized) or None
        """
        try:
            # Cannot easily access request body in middleware after it's been consumed
            # Return query params instead
            if request.query_params:
                return dict(request.query_params)
            return None
        except Exception as e:
            logger.warning(f"Could not extract request data: {e}")
            return None

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """
        Determine if endpoint handles sensitive data

        Args:
            path: Request path

        Returns:
            True if sensitive, False otherwise
        """
        sensitive_patterns = [
            "/auth/",
            "/vendors/me",
            "/square/",  # OAuth tokens
            "/feedback",  # May contain vendor comments
            "/data-export",  # GDPR export
        ]

        return any(pattern in path for pattern in sensitive_patterns)


# Helper function to add audit log from route handlers
def add_audit_log(
    db,
    vendor_id: str,
    action: str,
    user_email: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    changes_summary: str | None = None,
    request: Request | None = None,
    is_sensitive: bool = False,
) -> None:
    """
    Manually add audit log from route handler

    Use this for detailed auditing of specific operations
    where you need to capture old/new values.

    Args:
        db: Database session
        vendor_id: Vendor ID
        action: Action performed
        user_email: User email
        resource_type: Resource type
        resource_id: Resource ID
        old_values: State before change
        new_values: State after change
        changes_summary: Summary of changes
        request: FastAPI request (optional)
        is_sensitive: Contains sensitive data

    Example:
        from src.middleware.audit import add_audit_log
        from src.models.audit_log import AuditAction

        # In your route handler
        add_audit_log(
            db=db,
            vendor_id=vendor_id,
            action=AuditAction.UPDATE,
            user_email=vendor.email,
            resource_type="product",
            resource_id=product_id,
            old_values={"name": "Old Name", "price": 10.00},
            new_values={"name": "New Name", "price": 12.00},
            changes_summary="Updated product name and price",
        )
    """
    try:
        audit_service = AuditService(db)
        audit_service.log_action(
            vendor_id=vendor_id,
            action=action,
            user_id=vendor_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            request=request,
            is_sensitive=is_sensitive,
        )
    except Exception as e:
        logger.error(f"Failed to add audit log: {e}", exc_info=True)
