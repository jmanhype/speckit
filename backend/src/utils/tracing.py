"""OpenTelemetry distributed tracing for application monitoring.

Provides:
- Distributed tracing across services
- Automatic HTTP request instrumentation
- Database query tracing
- Custom span creation
- Integration with Jaeger/Zipkin/OTLP backends
"""
import functools
import logging
from typing import Callable, Optional, Dict, Any
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None


logger = logging.getLogger(__name__)


# =============================================================================
# Tracer Instance
# =============================================================================

if OPENTELEMETRY_AVAILABLE:
    # Global tracer instance
    tracer = trace.get_tracer(__name__)
else:
    tracer = None


# =============================================================================
# Setup Functions
# =============================================================================

def setup_tracing(
    service_name: str = "marketprep-backend",
    exporter_type: str = "console",
    exporter_endpoint: Optional[str] = None,
) -> None:
    """Setup OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing
        exporter_type: Type of exporter ('console', 'otlp', 'jaeger')
        exporter_endpoint: Endpoint for exporter (e.g., 'http://localhost:4317')

    Usage:
        # Development (console output)
        setup_tracing(service_name="marketprep-backend", exporter_type="console")

        # Production (OTLP to collector)
        setup_tracing(
            service_name="marketprep-backend",
            exporter_type="otlp",
            exporter_endpoint="http://otel-collector:4317"
        )

        # Production (Jaeger)
        setup_tracing(
            service_name="marketprep-backend",
            exporter_type="jaeger",
            exporter_endpoint="http://jaeger:14250"
        )
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available - tracing disabled")
        return

    # Create resource with service name
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Create exporter based on type
    if exporter_type == "console":
        exporter = ConsoleSpanExporter()
    elif exporter_type == "otlp":
        if not exporter_endpoint:
            raise ValueError("exporter_endpoint required for OTLP exporter")
        exporter = OTLPSpanExporter(endpoint=exporter_endpoint, insecure=True)
    elif exporter_type == "jaeger":
        if not exporter_endpoint:
            raise ValueError("exporter_endpoint required for Jaeger exporter")
        # Parse endpoint (format: http://host:port)
        import urllib.parse
        parsed = urllib.parse.urlparse(exporter_endpoint)
        exporter = JaegerExporter(
            agent_host_name=parsed.hostname,
            agent_port=parsed.port or 6831,
        )
    else:
        raise ValueError(f"Unknown exporter type: {exporter_type}")

    # Add span processor
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    logger.info(
        f"OpenTelemetry tracing configured: service={service_name}, "
        f"exporter={exporter_type}, endpoint={exporter_endpoint or 'N/A'}"
    )


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application for automatic tracing.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from src.utils.tracing import setup_tracing, instrument_fastapi

        app = FastAPI()
        setup_tracing()
        instrument_fastapi(app)
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available - FastAPI instrumentation disabled")
        return

    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented for OpenTelemetry tracing")


def instrument_requests() -> None:
    """Instrument requests library for automatic HTTP client tracing.

    Usage:
        from src.utils.tracing import setup_tracing, instrument_requests

        setup_tracing()
        instrument_requests()
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available - requests instrumentation disabled")
        return

    RequestsInstrumentor().instrument()
    logger.info("requests library instrumented for OpenTelemetry tracing")


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy for automatic database query tracing.

    Args:
        engine: SQLAlchemy engine instance

    Usage:
        from sqlalchemy import create_engine
        from src.utils.tracing import setup_tracing, instrument_sqlalchemy

        engine = create_engine(...)
        setup_tracing()
        instrument_sqlalchemy(engine)
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available - SQLAlchemy instrumentation disabled")
        return

    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy instrumented for OpenTelemetry tracing")


# =============================================================================
# Manual Span Creation
# =============================================================================

@contextmanager
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Create a custom span for tracing.

    Args:
        name: Span name
        attributes: Optional span attributes

    Usage:
        with create_span("process_recommendation", {"vendor_id": vendor_id}):
            # Your code here
            result = generate_recommendation()
    """
    if not OPENTELEMETRY_AVAILABLE or not tracer:
        yield
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield span


def trace_function(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to trace a function.

    Args:
        name: Optional span name (defaults to function name)
        attributes: Optional span attributes

    Usage:
        @trace_function(attributes={"service": "ml"})
        def generate_prediction():
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with create_span(span_name, attributes):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(span_name, attributes):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# Span Attribute Helpers
# =============================================================================

def set_span_attribute(key: str, value: Any) -> None:
    """Set attribute on current span.

    Args:
        key: Attribute key
        value: Attribute value

    Usage:
        def process_item(item_id: str):
            set_span_attribute("item_id", item_id)
            ...
    """
    if not OPENTELEMETRY_AVAILABLE or not trace:
        return

    span = trace.get_current_span()
    if span:
        span.set_attribute(key, str(value))


def set_span_error(error: Exception) -> None:
    """Mark current span as error.

    Args:
        error: Exception that occurred

    Usage:
        try:
            risky_operation()
        except Exception as e:
            set_span_error(e)
            raise
    """
    if not OPENTELEMETRY_AVAILABLE or not trace:
        return

    span = trace.get_current_span()
    if span:
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
        span.record_exception(error)


# =============================================================================
# Context Propagation
# =============================================================================

def get_trace_context() -> Dict[str, str]:
    """Get current trace context for propagation.

    Returns:
        Dictionary of trace context headers

    Usage:
        # Propagate trace context to external service
        context = get_trace_context()
        headers = {"X-Trace-Context": context}
        requests.get("http://external-api", headers=headers)
    """
    if not OPENTELEMETRY_AVAILABLE or not trace:
        return {}

    from opentelemetry.propagate import inject

    context_dict = {}
    inject(context_dict)
    return context_dict


# =============================================================================
# Business Logic Tracing Helpers
# =============================================================================

@contextmanager
def trace_recommendation_generation(vendor_id: str, market_date: str):
    """Trace recommendation generation with context.

    Args:
        vendor_id: Vendor ID
        market_date: Market date

    Usage:
        with trace_recommendation_generation(vendor_id, market_date):
            recommendation = ml_service.generate(vendor_id, market_date)
    """
    attributes = {
        "vendor_id": vendor_id,
        "market_date": market_date,
        "operation": "recommendation_generation"
    }
    with create_span("generate_recommendation", attributes):
        yield


@contextmanager
def trace_external_api_call(api_name: str, operation: str, **kwargs):
    """Trace external API call with context.

    Args:
        api_name: API name (e.g., 'square', 'weather', 'eventbrite')
        operation: Operation name (e.g., 'catalog', 'forecast', 'events')
        **kwargs: Additional attributes

    Usage:
        with trace_external_api_call("square", "catalog", vendor_id=vendor_id):
            result = square_client.list_catalog()
    """
    attributes = {
        "api_name": api_name,
        "operation": operation,
        **{k: str(v) for k, v in kwargs.items()}
    }
    with create_span(f"{api_name}.{operation}", attributes):
        yield


@contextmanager
def trace_database_operation(table: str, operation: str, **kwargs):
    """Trace database operation with context.

    Args:
        table: Table name
        operation: Operation (select, insert, update, delete)
        **kwargs: Additional attributes

    Usage:
        with trace_database_operation("recommendations", "select", vendor_id=vendor_id):
            result = db.query(Recommendation).filter(...).all()
    """
    attributes = {
        "db.table": table,
        "db.operation": operation,
        **{k: str(v) for k, v in kwargs.items()}
    }
    with create_span(f"db.{table}.{operation}", attributes):
        yield


# =============================================================================
# Configuration from Environment
# =============================================================================

def setup_tracing_from_config() -> None:
    """Setup tracing from application configuration.

    Reads from environment variables:
    - OTEL_ENABLED: Enable/disable tracing
    - OTEL_SERVICE_NAME: Service name
    - OTEL_EXPORTER_TYPE: Exporter type (console, otlp, jaeger)
    - OTEL_EXPORTER_ENDPOINT: Exporter endpoint

    Usage:
        # In application startup
        from src.utils.tracing import setup_tracing_from_config

        setup_tracing_from_config()
    """
    import os

    enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false)")
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "marketprep-backend")
    exporter_type = os.getenv("OTEL_EXPORTER_TYPE", "console")
    exporter_endpoint = os.getenv("OTEL_EXPORTER_ENDPOINT")

    setup_tracing(
        service_name=service_name,
        exporter_type=exporter_type,
        exporter_endpoint=exporter_endpoint
    )
