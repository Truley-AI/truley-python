"""OpenTelemetry tracing with auto-instrumentation.

Must call init_tracing() before importing FastAPI/httpx.

Usage:
    from truley_python.tracing import init_tracing
    init_tracing("http://localhost:4318", "my-service")

    from fastapi import FastAPI  # Now instrumented
"""

from typing import TypedDict

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False
_service_name: str | None = None


class TraceContext(TypedDict):
    trace_id: str
    span_id: str


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized."""
    return _initialized


def get_service_name() -> str | None:
    """Get the service name set by init_tracing."""
    return _service_name


def get_current_trace_context() -> TraceContext | None:
    """Get current trace context if available."""
    if not _initialized:
        return None

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


def init_tracing(endpoint: str, service_name: str) -> None:
    """Initialize OpenTelemetry tracing.

    Args:
        endpoint: OTLP HTTP endpoint (e.g., http://localhost:4318)
        service_name: Service name for traces (e.g., "backend")
    """
    global _initialized, _service_name

    if _initialized:
        return

    _service_name = service_name

    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)

    _initialized = True
