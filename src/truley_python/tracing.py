"""OpenTelemetry tracing with auto-instrumentation for FastAPI and httpx.

Example:
    # main.py
    from truley_python.tracing import init_tracing
    init_tracing("backend", "http://localhost:4317")  # Before FastAPI!

    from fastapi import FastAPI  # Now it's patched
"""

from typing import TypedDict

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized."""
    return _initialized


class TraceContext(TypedDict):
    trace_id: str
    span_id: str


def get_current_trace_context() -> TraceContext | None:
    """Get current trace context (trace_id, span_id) if available.

    Returns:
        TraceContext dict with trace_id and span_id, or None if no active span.

    Example:
        >>> ctx = get_current_trace_context()
        >>> if ctx:
        ...     print(f"trace_id: {ctx['trace_id']}")
    """
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


def init_tracing(
    service_name: str,
    otlp_endpoint: str,
) -> None:
    """Initialize OpenTelemetry tracing with auto-instrumentation.

    IMPORTANT: Call this BEFORE importing FastAPI, httpx, or any other
    instrumented libraries.

    This function sets up:
    - OTLP exporter
    - FastAPI auto-instrumentation
    - httpx auto-instrumentation

    Args:
        service_name: Service name for traces (e.g., "backend", "analyzer")
        otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")

    Example:
        >>> from truley_python.tracing import init_tracing
        >>> init_tracing("backend", "http://tempo:4317")
    """
    global _initialized

    if _initialized:
        return

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Create and set tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI and httpx
    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    _initialized = True
