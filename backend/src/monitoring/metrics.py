"""
Prometheus Metrics for MarketPrep

Exposes application metrics in Prometheus format for monitoring:
- HTTP request metrics (count, duration, status codes)
- Database query metrics
- External API call metrics (Square, Weather, Events)
- ML prediction metrics
- Business metrics (recommendations generated, products synced)
- System metrics (memory, CPU)

Metrics are exposed at /metrics endpoint for Prometheus scraping.
"""

from typing import Optional
import time
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from starlette.responses import Response

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    "marketprep_app",
    "MarketPrep application information",
    registry=registry,
)
app_info.info({
    "version": settings.app_version,
    "environment": settings.environment,
})

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    "marketprep_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "marketprep_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

http_requests_in_progress = Gauge(
    "marketprep_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry,
)

http_response_size_bytes = Histogram(
    "marketprep_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
    registry=registry,
)

# ============================================================================
# Database Metrics
# ============================================================================

db_queries_total = Counter(
    "marketprep_db_queries_total",
    "Total database queries",
    ["operation"],  # SELECT, INSERT, UPDATE, DELETE
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "marketprep_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

db_connections_active = Gauge(
    "marketprep_db_connections_active",
    "Number of active database connections",
    registry=registry,
)

db_errors_total = Counter(
    "marketprep_db_errors_total",
    "Total database errors",
    ["error_type"],
    registry=registry,
)

# ============================================================================
# External API Metrics
# ============================================================================

external_api_calls_total = Counter(
    "marketprep_external_api_calls_total",
    "Total external API calls",
    ["service", "endpoint", "status"],  # service: square, weather, events
    registry=registry,
)

external_api_duration_seconds = Histogram(
    "marketprep_external_api_duration_seconds",
    "External API call duration in seconds",
    ["service", "endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry,
)

external_api_errors_total = Counter(
    "marketprep_external_api_errors_total",
    "Total external API errors",
    ["service", "error_type"],
    registry=registry,
)

# ============================================================================
# ML Prediction Metrics
# ============================================================================

ml_predictions_total = Counter(
    "marketprep_ml_predictions_total",
    "Total ML predictions generated",
    ["model_type"],  # ml_model, fallback_heuristic
    registry=registry,
)

ml_prediction_duration_seconds = Histogram(
    "marketprep_ml_prediction_duration_seconds",
    "ML prediction duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    registry=registry,
)

ml_prediction_confidence = Histogram(
    "marketprep_ml_prediction_confidence",
    "ML prediction confidence scores",
    ["model_type"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=registry,
)

ml_model_load_time_seconds = Gauge(
    "marketprep_ml_model_load_time_seconds",
    "Time taken to load ML model",
    registry=registry,
)

# ============================================================================
# Business Metrics
# ============================================================================

recommendations_generated_total = Counter(
    "marketprep_recommendations_generated_total",
    "Total recommendations generated",
    ["vendor_id"],
    registry=registry,
)

recommendations_accepted_total = Counter(
    "marketprep_recommendations_accepted_total",
    "Total recommendations accepted by vendors",
    ["vendor_id"],
    registry=registry,
)

feedback_submitted_total = Counter(
    "marketprep_feedback_submitted_total",
    "Total feedback submissions",
    ["rating"],  # 1-5 stars
    registry=registry,
)

feedback_accuracy_rate = Gauge(
    "marketprep_feedback_accuracy_rate",
    "Percentage of recommendations that were accurate (±20%)",
    registry=registry,
)

square_products_synced_total = Counter(
    "marketprep_square_products_synced_total",
    "Total products synced from Square",
    ["vendor_id"],
    registry=registry,
)

square_sync_duration_seconds = Histogram(
    "marketprep_square_sync_duration_seconds",
    "Square product sync duration in seconds",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=registry,
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    "marketprep_cache_hits_total",
    "Total cache hits",
    ["cache_key_prefix"],
    registry=registry,
)

cache_misses_total = Counter(
    "marketprep_cache_misses_total",
    "Total cache misses",
    ["cache_key_prefix"],
    registry=registry,
)

cache_errors_total = Counter(
    "marketprep_cache_errors_total",
    "Total cache errors (Redis failures)",
    ["operation"],  # get, set, delete
    registry=registry,
)

# ============================================================================
# System Metrics
# ============================================================================

system_memory_usage_bytes = Gauge(
    "marketprep_system_memory_usage_bytes",
    "System memory usage in bytes",
    registry=registry,
)

system_cpu_usage_percent = Gauge(
    "marketprep_system_cpu_usage_percent",
    "System CPU usage percentage",
    registry=registry,
)

# ============================================================================
# Metric Helpers / Decorators
# ============================================================================


def track_api_call(service: str, endpoint: str):
    """
    Decorator to track external API calls

    Usage:
        @track_api_call('square', 'list_catalog')
        async def list_catalog_items(self):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            error_type = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_type = type(e).__name__
                external_api_errors_total.labels(
                    service=service,
                    error_type=error_type,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                external_api_calls_total.labels(
                    service=service,
                    endpoint=endpoint,
                    status=status,
                ).inc()
                external_api_duration_seconds.labels(
                    service=service,
                    endpoint=endpoint,
                ).observe(duration)

        return wrapper
    return decorator


def track_db_query(operation: str):
    """
    Decorator to track database queries

    Usage:
        @track_db_query('SELECT')
        async def get_user(self, user_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            error_type = None

            try:
                result = await func(*args, **kwargs)
                db_queries_total.labels(operation=operation).inc()
                return result
            except Exception as e:
                error_type = type(e).__name__
                db_errors_total.labels(error_type=error_type).inc()
                raise
            finally:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def track_ml_prediction(model_type: str = "ml_model"):
    """
    Decorator to track ML predictions

    Usage:
        @track_ml_prediction('ml_model')
        def predict_quantity(self, features):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                ml_predictions_total.labels(model_type=model_type).inc()

                # Track confidence if available
                if isinstance(result, dict) and "confidence_score" in result:
                    ml_prediction_confidence.labels(model_type=model_type).observe(
                        result["confidence_score"]
                    )

                return result
            finally:
                duration = time.time() - start_time
                ml_prediction_duration_seconds.observe(duration)

        return wrapper
    return decorator


class MetricsCollector:
    """Helper class for collecting business metrics"""

    @staticmethod
    def record_recommendation_generated(vendor_id: str):
        """Record that a recommendation was generated"""
        recommendations_generated_total.labels(vendor_id=vendor_id).inc()

    @staticmethod
    def record_recommendation_accepted(vendor_id: str):
        """Record that a vendor accepted a recommendation"""
        recommendations_accepted_total.labels(vendor_id=vendor_id).inc()

    @staticmethod
    def record_feedback_submitted(rating: int):
        """Record feedback submission"""
        feedback_submitted_total.labels(rating=str(rating)).inc()

    @staticmethod
    def update_feedback_accuracy_rate(accuracy_rate: float):
        """Update overall feedback accuracy rate"""
        feedback_accuracy_rate.set(accuracy_rate)

    @staticmethod
    def record_square_sync(vendor_id: str, duration_seconds: float, product_count: int):
        """Record Square product sync"""
        square_products_synced_total.labels(vendor_id=vendor_id).inc(product_count)
        square_sync_duration_seconds.observe(duration_seconds)

    @staticmethod
    def record_cache_hit(cache_key_prefix: str):
        """Record cache hit"""
        cache_hits_total.labels(cache_key_prefix=cache_key_prefix).inc()

    @staticmethod
    def record_cache_miss(cache_key_prefix: str):
        """Record cache miss"""
        cache_misses_total.labels(cache_key_prefix=cache_key_prefix).inc()

    @staticmethod
    def record_cache_error(operation: str):
        """Record cache error"""
        cache_errors_total.labels(operation=operation).inc()

    @staticmethod
    def update_system_metrics(memory_bytes: int, cpu_percent: float):
        """Update system resource metrics"""
        system_memory_usage_bytes.set(memory_bytes)
        system_cpu_usage_percent.set(cpu_percent)


def metrics_response() -> Response:
    """
    Generate Prometheus metrics response

    Returns Response with Content-Type: text/plain; version=0.0.4
    """
    metrics_data = generate_latest(registry)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# Initialization
# ============================================================================

def initialize_metrics():
    """Initialize metrics on application startup"""
    logger.info("Prometheus metrics initialized")
    logger.info(f"Metrics will be exposed at /metrics endpoint")
    logger.info(f"Application version: {settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
