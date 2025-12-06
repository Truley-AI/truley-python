# truley-python

Truley internal Python shared package providing structured logging.

## Installation

```bash
uv add truley-python
```

Or using pip:

```bash
pip install truley-python
```

## Usage

### Basic Usage

```python
from truley_python import create_logger

logger = create_logger("my-service")

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
logger = create_logger("my-service", level="debug")
```

### Output Formats

**JSON format (default)** - Suitable for production:

```python
logger = create_logger("backend")
logger.info("Meeting created", tenantId="t-123", meetingId="m-456")
# {"level":"info","time":1700000000000,"msg":"Meeting created","service":"backend","tenantId":"t-123","meetingId":"m-456"}
```

**Pretty format** - Suitable for development:

```python
logger = create_logger("backend", pretty=True)
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
