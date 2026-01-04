"""OpenTelemetry tracing with auto-instrumentation.

Auto-initializes on import if OTEL_EXPORTER_OTLP_ENDPOINT is set.
Must be imported before FastAPI/httpx.

Usage:
    import truley_python.tracing  # Auto-initializes

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT: Required. (e.g., http://localhost:4318)
    OTEL_SERVICE_NAME: Optional. (default: unknown)
    NODE_ENV or ENVIRONMENT: Optional. (default: development)
"""

import os
from typing import TypedDict

_initialized = False


class TraceContext(TypedDict):
    trace_id: str
    span_id: str


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized."""
    return _initialized


def get_current_trace_context() -> TraceContext | None:
    """Get current trace context if available."""
    if not _initialized:
        return None

    from opentelemetry import trace

    span = trace.get_current_span()
    if span is None:
        return None

    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None

    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }


def init_tracing(service_name: str | None = None) -> bool:
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Override service name (default: OTEL_SERVICE_NAME or 'unknown')

    Returns:
        True if initialized, False if OTEL_EXPORTER_OTLP_ENDPOINT not set.
    """
    global _initialized

    if _initialized:
        return True

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service = service_name or os.environ.get("OTEL_SERVICE_NAME", "unknown")
    environment = os.environ.get("NODE_ENV") or os.environ.get(
        "ENVIRONMENT", "development"
    )

    resource = Resource.create(
        {
            "service.name": service,
            "deployment.environment": environment,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)

    _initialized = True
    return True


# Auto-initialize on import
init_tracing()
