"""Prometheus metrics collection for application monitoring.

Provides:
- Request metrics (count, duration, size)
- Business metrics (recommendations generated, API calls)
- System metrics (database connections, cache hit rate)
- Custom gauge/counter/histogram decorators
"""
import functools
import time
from typing import Callable, Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# =============================================================================
# HTTP Request Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Request counter by method, endpoint, and status
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code']
    )

    # Request duration histogram
    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint'],
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
    )

    # Request size histogram
    http_request_size_bytes = Histogram(
        'http_request_size_bytes',
        'HTTP request size in bytes',
        ['method', 'endpoint']
    )

    # Response size histogram
    http_response_size_bytes = Histogram(
        'http_response_size_bytes',
        'HTTP response size in bytes',
        ['method', 'endpoint']
    )


# =============================================================================
# Business Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Recommendations generated
    recommendations_generated_total = Counter(
        'recommendations_generated_total',
        'Total recommendations generated',
        ['vendor_id']
    )

    # Square API calls
    square_api_calls_total = Counter(
        'square_api_calls_total',
        'Total Square API calls',
        ['operation', 'status']  # status: success, error, cached
    )

    # Weather API calls
    weather_api_calls_total = Counter(
        'weather_api_calls_total',
        'Total Weather API calls',
        ['status']  # status: success, error, cached
    )

    # Eventbrite API calls
    events_api_calls_total = Counter(
        'events_api_calls_total',
        'Total Eventbrite API calls',
        ['status']  # status: success, error, cached
    )

    # ML model predictions
    ml_predictions_total = Counter(
        'ml_predictions_total',
        'Total ML predictions',
        ['model_type']
    )

    # ML prediction confidence (average)
    ml_prediction_confidence = Histogram(
        'ml_prediction_confidence',
        'ML prediction confidence scores',
        ['model_type'],
        buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
    )


# =============================================================================
# Database Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Database connection pool
    db_connections_active = Gauge(
        'db_connections_active',
        'Active database connections'
    )

    # Database query duration
    db_query_duration_seconds = Histogram(
        'db_query_duration_seconds',
        'Database query duration in seconds',
        ['table', 'operation'],
        buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
    )

    # Database query errors
    db_query_errors_total = Counter(
        'db_query_errors_total',
        'Total database query errors',
        ['table', 'error_type']
    )


# =============================================================================
# Cache Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Redis cache hits/misses
    cache_operations_total = Counter(
        'cache_operations_total',
        'Total cache operations',
        ['operation', 'result']  # operation: get, set, delete; result: hit, miss, error
    )

    # Cache size
    cache_size_bytes = Gauge(
        'cache_size_bytes',
        'Total size of cached data in bytes',
        ['cache_type']
    )


# =============================================================================
# Authentication Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Authentication attempts
    auth_attempts_total = Counter(
        'auth_attempts_total',
        'Total authentication attempts',
        ['result']  # result: success, failed, invalid_token
    )

    # Active sessions
    active_sessions = Gauge(
        'active_sessions',
        'Number of active user sessions'
    )


# =============================================================================
# Error Tracking Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Application errors
    application_errors_total = Counter(
        'application_errors_total',
        'Total application errors',
        ['error_type', 'severity']
    )

    # External API errors
    external_api_errors_total = Counter(
        'external_api_errors_total',
        'Total external API errors',
        ['api_name', 'error_type']
    )


# =============================================================================
# Decorator Functions
# =============================================================================

def track_request_metrics(endpoint: str):
    """Decorator to track HTTP request metrics.

    Args:
        endpoint: Endpoint name for metric labeling

    Usage:
        @track_request_metrics('/api/v1/recommendations')
        async def get_recommendations():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Track duration
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    method='GET',  # TODO: Extract from request
                    endpoint=endpoint
                ).observe(duration)

                return result
            except Exception as e:
                # Track error
                application_errors_total.labels(
                    error_type=type(e).__name__,
                    severity='error'
                ).inc()
                raise

        return wrapper
    return decorator


def track_db_query(table: str, operation: str = 'select'):
    """Decorator to track database query metrics.

    Args:
        table: Database table name
        operation: Query operation (select, insert, update, delete)

    Usage:
        @track_db_query('recommendations', 'select')
        def get_recommendations_from_db():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Track duration
                duration = time.time() - start_time
                db_query_duration_seconds.labels(
                    table=table,
                    operation=operation
                ).observe(duration)

                return result
            except Exception as e:
                # Track error
                db_query_errors_total.labels(
                    table=table,
                    error_type=type(e).__name__
                ).inc()
                raise

        return wrapper
    return decorator


def track_external_api(api_name: str, operation: str):
    """Decorator to track external API call metrics.

    Args:
        api_name: External API name (e.g., 'square', 'weather', 'eventbrite')
        operation: API operation (e.g., 'catalog', 'forecast', 'events')

    Usage:
        @track_external_api('square', 'catalog')
        async def fetch_square_catalog():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)

            try:
                result = await func(*args, **kwargs)

                # Track successful call
                if api_name == 'square':
                    square_api_calls_total.labels(
                        operation=operation,
                        status='success'
                    ).inc()
                elif api_name == 'weather':
                    weather_api_calls_total.labels(status='success').inc()
                elif api_name == 'eventbrite':
                    events_api_calls_total.labels(status='success').inc()

                return result
            except Exception as e:
                # Track error
                if api_name == 'square':
                    square_api_calls_total.labels(
                        operation=operation,
                        status='error'
                    ).inc()
                elif api_name == 'weather':
                    weather_api_calls_total.labels(status='error').inc()
                elif api_name == 'eventbrite':
                    events_api_calls_total.labels(status='error').inc()

                external_api_errors_total.labels(
                    api_name=api_name,
                    error_type=type(e).__name__
                ).inc()
                raise

        return wrapper
    return decorator


# =============================================================================
# Utility Functions
# =============================================================================

def record_recommendation_generated(vendor_id: str) -> None:
    """Record that a recommendation was generated.

    Args:
        vendor_id: ID of vendor for whom recommendation was generated
    """
    if PROMETHEUS_AVAILABLE:
        recommendations_generated_total.labels(vendor_id=vendor_id).inc()


def record_ml_prediction(model_type: str, confidence: float) -> None:
    """Record ML model prediction with confidence score.

    Args:
        model_type: Type of ML model (e.g., 'random_forest', 'gradient_boost')
        confidence: Prediction confidence score (0.0 to 1.0)
    """
    if PROMETHEUS_AVAILABLE:
        ml_predictions_total.labels(model_type=model_type).inc()
        ml_prediction_confidence.labels(model_type=model_type).observe(confidence)


def record_cache_operation(operation: str, result: str) -> None:
    """Record cache operation (hit/miss/error).

    Args:
        operation: Cache operation ('get', 'set', 'delete')
        result: Operation result ('hit', 'miss', 'error')
    """
    if PROMETHEUS_AVAILABLE:
        cache_operations_total.labels(operation=operation, result=result).inc()


def record_auth_attempt(result: str) -> None:
    """Record authentication attempt.

    Args:
        result: Authentication result ('success', 'failed', 'invalid_token')
    """
    if PROMETHEUS_AVAILABLE:
        auth_attempts_total.labels(result=result).inc()


def get_metrics() -> tuple[bytes, str]:
    """Get Prometheus metrics in exposition format.

    Returns:
        Tuple of (metrics_bytes, content_type)
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# Prometheus client not installed\n", "text/plain"

    return generate_latest(), CONTENT_TYPE_LATEST


# =============================================================================
# FastAPI Integration
# =============================================================================

def setup_metrics_endpoint(app):
    """Setup /metrics endpoint for Prometheus scraping.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from src.utils.metrics import setup_metrics_endpoint

        app = FastAPI()
        setup_metrics_endpoint(app)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    from fastapi import Response

    @app.get("/metrics")
    async def metrics():
        """Expose Prometheus metrics."""
        metrics_bytes, content_type = get_metrics()
        return Response(content=metrics_bytes, media_type=content_type)
