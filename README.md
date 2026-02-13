# truley-python

Truley internal Python shared package.

## Installation

```bash
uv add truley-python
```

Or using pip:

```bash
pip install truley-python
```

## Console Logger

Structured logging module for console output.

### Basic Usage

```python
from truley_python import console_logger

logger = console_logger.create_logger("my-service")

logger.info("Server started", port=8080)
logger.debug("Processing request", request_id="req-123")
logger.warn("High memory usage", usage_percent=85)
logger.error("Failed to connect", error=exception, host="db.example.com")
```

### Log Levels

Supported levels (from lowest to highest):

- `debug` - Debug information
- `verbose` - Verbose information (same as debug)
- `info` - General information
- `warn` - Warnings
- `error` - Errors
- `fatal` - Critical errors

```python
logger = console_logger.create_logger("my-service", level="debug")
```

### Output Formats

**JSON format (default)** - Suitable for production:

```python
logger = console_logger.create_logger("backend")
logger.info("Meeting created", tenantId="t-123", meetingId="m-456")
# {"level":"info","time":1700000000000,"msg":"Meeting created","service":"backend","tenantId":"t-123","meetingId":"m-456"}
```

**Pretty format** - Suitable for development:

```python
logger = console_logger.create_logger("backend", pretty=True)
logger.info("Meeting created", tenantId="t-123")
# [2024-01-15 10:30:00] INFO: Meeting created
#     tenantId: t-123
```

### Error Logging

When logging exceptions, it automatically captures error type, message, and full stack trace:

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", error=e, operation="risky_operation")
```

Output:

```json
{
  "level": "error",
  "time": 1700000000000,
  "msg": "Operation failed",
  "service": "my-service",
  "operation": "risky_operation",
  "error": {
    "type": "ValueError",
    "message": "Invalid input",
    "stack": "Traceback (most recent call last):..."
  }
}
```

### Intercepting Stdlib Logging

Forward logs from libraries like uvicorn and fastapi to the structured logger:

```python
from truley_python import console_logger

logger = console_logger.create_logger("my-service")

console_logger.intercept_stdlib_logging(logger, [
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
])
```

## Tracing

OpenTelemetry tracing with auto-instrumentation for distributed tracing.

### Initialization

Must call `init_tracing()` before importing FastAPI/httpx:

```python
from truley_python.tracing import init_tracing

init_tracing("http://localhost:4318", "my-service")

from fastapi import FastAPI  # Now auto-instrumented
```

### Auto-instrumented Libraries

- FastAPI
- httpx
- requests
- logging

### Get Trace Context

```python
from truley_python.tracing import get_current_trace_context

ctx = get_current_trace_context()
# {"trace_id": "0123456789abcdef...", "span_id": "0123456789abcdef"}
```

### Baggage

Baggage allows passing context across services in distributed tracing.

```python
from truley_python.tracing import get_baggage

# Get a baggage value from the current context
user_id = get_baggage("user_id")  # Returns str | None
tenant = get_baggage("tenant")
```

## Development

### Setup

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Code Quality

This project uses:

- **ruff** - Linting and formatting
- **mypy** - Static type checking
- **pre-commit** - Git hooks

```bash
# Run linter
uv run ruff check .

# Run formatter
uv run ruff format .

# Run type checker
uv run mypy src
```

## License

MIT
