"""Error tracking integration with Sentry for production monitoring.

Provides:
- Automatic error capture and reporting
- User context tracking
- Performance monitoring
- Release tracking
- Environment tagging
- Custom error grouping
"""
import functools
import logging
from typing import Callable, Optional, Dict, Any

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None


logger = logging.getLogger(__name__)


# =============================================================================
# Setup Functions
# =============================================================================

def setup_sentry(
    dsn: str,
    environment: str = "production",
    release: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True,
) -> None:
    """Setup Sentry error tracking and performance monitoring.

    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (production, staging, development)
        release: Release version (e.g., 'v1.0.0', git SHA)
        traces_sample_rate: Percentage of transactions to trace (0.0 to 1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0 to 1.0)
        enable_tracing: Enable performance tracing

    Usage:
        from src.utils.error_tracking import setup_sentry

        setup_sentry(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            environment="production",
            release="v1.2.3",
            traces_sample_rate=0.1  # 10% of transactions
        )
    """
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not available - error tracking disabled")
        return

    if not dsn:
        logger.warning("Sentry DSN not provided - error tracking disabled")
        return

    # Configure integrations
    integrations = [
        # FastAPI integration (automatic route tracking)
        FastApiIntegration(
            transaction_style="endpoint"  # Group by endpoint, not URL
        ),
        # SQLAlchemy integration (database query tracking)
        SqlalchemyIntegration(),
        # Redis integration (cache operation tracking)
        RedisIntegration(),
        # Logging integration (capture log messages)
        LoggingIntegration(
            level=logging.INFO,  # Capture info and above
            event_level=logging.ERROR  # Create events for errors and above
        ),
    ]

    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=integrations,
        # Performance monitoring
        traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
        profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
        # Error sampling (100% - capture all errors)
        sample_rate=1.0,
        # Send default PII (Personally Identifiable Information)
        send_default_pii=False,  # Important: Don't send PII by default (GDPR compliance)
        # Debug mode (verbose logging)
        debug=False,
        # Attach stack trace to messages
        attach_stacktrace=True,
        # Max breadcrumbs to store
        max_breadcrumbs=50,
        # Before send hook (can filter/modify events)
        before_send=_before_send_hook,
    )

    logger.info(
        f"Sentry initialized: environment={environment}, "
        f"release={release}, traces_sample_rate={traces_sample_rate}"
    )


def setup_sentry_from_config() -> None:
    """Setup Sentry from application configuration.

    Reads from environment variables:
    - SENTRY_DSN: Sentry DSN
    - SENTRY_ENVIRONMENT: Environment name
    - SENTRY_RELEASE: Release version
    - SENTRY_TRACES_SAMPLE_RATE: Trace sampling rate
    - SENTRY_PROFILES_SAMPLE_RATE: Profile sampling rate

    Usage:
        # In application startup
        from src.utils.error_tracking import setup_sentry_from_config

        setup_sentry_from_config()
    """
    import os

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return

    environment = os.getenv("SENTRY_ENVIRONMENT", "production")
    release = os.getenv("SENTRY_RELEASE")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    setup_sentry(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
    )


# =============================================================================
# Event Filtering
# =============================================================================

def _before_send_hook(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Hook called before sending event to Sentry.

    Can be used to:
    - Filter out certain errors
    - Scrub sensitive data
    - Add custom context
    - Modify error grouping

    Args:
        event: Event data
        hint: Additional context (contains exception if available)

    Returns:
        Modified event or None to drop the event
    """
    # Get exception if available
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Filter out specific exceptions
        if exc_type.__name__ in ["KeyboardInterrupt", "SystemExit"]:
            return None

        # Filter out HTTP 404 errors (not exceptional)
        if exc_type.__name__ == "HTTPException" and hasattr(exc_value, "status_code"):
            if exc_value.status_code == 404:
                return None

    # Scrub sensitive data from request
    if "request" in event:
        request = event["request"]

        # Remove sensitive headers
        if "headers" in request:
            sensitive_headers = ["Authorization", "Cookie", "X-API-Key"]
            for header in sensitive_headers:
                if header in request["headers"]:
                    request["headers"][header] = "[Filtered]"

        # Remove sensitive query params
        if "query_string" in request:
            # Could parse and filter specific params
            pass

    # Add custom fingerprinting for better grouping
    if "exception" in event and "values" in event["exception"]:
        for exception in event["exception"]["values"]:
            # Group by exception type and message pattern
            if exception.get("type") == "ValidationError":
                event["fingerprint"] = ["{{ default }}", "validation-error"]

    return event


# =============================================================================
# Context Management
# =============================================================================

def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs
) -> None:
    """Set user context for error reports.

    Args:
        user_id: User ID
        email: User email (will be scrubbed if send_default_pii=False)
        username: Username
        **kwargs: Additional user attributes

    Usage:
        from src.utils.error_tracking import set_user_context

        set_user_context(user_id="vendor_123", username="bakery_shop")
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    user_data = {
        "id": user_id,
        "email": email,
        "username": username,
        **kwargs
    }

    # Remove None values
    user_data = {k: v for k, v in user_data.items() if v is not None}

    sentry_sdk.set_user(user_data)


def set_context(name: str, data: Dict[str, Any]) -> None:
    """Set custom context for error reports.

    Args:
        name: Context name
        data: Context data

    Usage:
        from src.utils.error_tracking import set_context

        set_context("recommendation", {
            "vendor_id": vendor_id,
            "market_date": market_date,
            "product_count": len(products)
        })
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    sentry_sdk.set_context(name, data)


def set_tag(key: str, value: str) -> None:
    """Set tag for error filtering and grouping.

    Args:
        key: Tag key
        value: Tag value

    Usage:
        from src.utils.error_tracking import set_tag

        set_tag("api_version", "v1")
        set_tag("feature", "recommendations")
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    sentry_sdk.set_tag(key, value)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Add breadcrumb for debugging context.

    Breadcrumbs are chronological logs that lead up to an error.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category (e.g., 'auth', 'database', 'api')
        level: Log level ('debug', 'info', 'warning', 'error', 'fatal')
        data: Additional breadcrumb data

    Usage:
        from src.utils.error_tracking import add_breadcrumb

        add_breadcrumb(
            message="Fetching products from Square",
            category="api",
            level="info",
            data={"vendor_id": vendor_id}
        )
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# =============================================================================
# Manual Error Capture
# =============================================================================

def capture_exception(
    error: Exception,
    level: str = "error",
    tags: Optional[Dict[str, str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Manually capture an exception.

    Args:
        error: Exception to capture
        level: Severity level ('debug', 'info', 'warning', 'error', 'fatal')
        tags: Tags for filtering
        context: Additional context

    Returns:
        Event ID (can be shown to user for support)

    Usage:
        from src.utils.error_tracking import capture_exception

        try:
            risky_operation()
        except Exception as e:
            event_id = capture_exception(
                e,
                tags={"operation": "recommendation_generation"},
                context={"vendor_id": vendor_id}
            )
            logger.error(f"Error captured: {event_id}")
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return None

    # Set tags
    if tags:
        for key, value in tags.items():
            set_tag(key, value)

    # Set context
    if context:
        set_context("error_context", context)

    # Capture exception
    event_id = sentry_sdk.capture_exception(error, level=level)

    return event_id


def capture_message(
    message: str,
    level: str = "info",
    tags: Optional[Dict[str, str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Manually capture a message.

    Args:
        message: Message to capture
        level: Severity level ('debug', 'info', 'warning', 'error', 'fatal')
        tags: Tags for filtering
        context: Additional context

    Returns:
        Event ID

    Usage:
        from src.utils.error_tracking import capture_message

        capture_message(
            "Unusual activity detected",
            level="warning",
            tags={"feature": "recommendations"},
            context={"vendor_id": vendor_id, "anomaly_score": 0.95}
        )
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return None

    # Set tags
    if tags:
        for key, value in tags.items():
            set_tag(key, value)

    # Set context
    if context:
        set_context("message_context", context)

    # Capture message
    event_id = sentry_sdk.capture_message(message, level=level)

    return event_id


# =============================================================================
# Decorator for Error Tracking
# =============================================================================

def track_errors(
    operation: str,
    capture_args: bool = False,
):
    """Decorator to automatically track errors in a function.

    Args:
        operation: Operation name for tagging
        capture_args: Capture function arguments in context

    Usage:
        @track_errors("recommendation_generation", capture_args=True)
        async def generate_recommendation(vendor_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            set_tag("operation", operation)

            if capture_args and SENTRY_AVAILABLE:
                # Capture function arguments (be careful with sensitive data!)
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                set_context("function_args", dict(bound_args.arguments))

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Add breadcrumb for function call
                add_breadcrumb(
                    message=f"Error in {operation}",
                    category="function",
                    level="error",
                    data={"function": func.__name__}
                )

                # Exception will be auto-captured by Sentry
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            set_tag("operation", operation)

            if capture_args and SENTRY_AVAILABLE:
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                set_context("function_args", dict(bound_args.arguments))

            try:
                return func(*args, **kwargs)
            except Exception as e:
                add_breadcrumb(
                    message=f"Error in {operation}",
                    category="function",
                    level="error",
                    data={"function": func.__name__}
                )
                raise

        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# Performance Monitoring
# =============================================================================

def start_transaction(
    name: str,
    op: str = "http.server",
    **kwargs
):
    """Start a new Sentry transaction for performance monitoring.

    Args:
        name: Transaction name (e.g., 'GET /api/recommendations')
        op: Operation type (e.g., 'http.server', 'db.query', 'task')
        **kwargs: Additional transaction data

    Returns:
        Transaction context manager

    Usage:
        from src.utils.error_tracking import start_transaction

        with start_transaction("generate_recommendations", op="task"):
            recommendation = ml_service.generate(vendor_id, market_date)
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        from contextlib import nullcontext
        return nullcontext()

    return sentry_sdk.start_transaction(name=name, op=op, **kwargs)


# =============================================================================
# Utility Functions
# =============================================================================

def flush(timeout: float = 2.0) -> bool:
    """Flush pending events to Sentry.

    Useful before application shutdown.

    Args:
        timeout: Timeout in seconds

    Returns:
        True if all events were sent

    Usage:
        from src.utils.error_tracking import flush

        # On application shutdown
        flush(timeout=5.0)
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return True

    return sentry_sdk.flush(timeout=timeout)
