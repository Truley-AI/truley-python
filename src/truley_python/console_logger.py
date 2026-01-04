import logging
import sys
import traceback
from typing import Any, Literal

from loguru import logger as _loguru_logger

LevelStr = Literal["debug", "verbose", "info", "warn", "error", "fatal"]


def _serialize(record: dict[str, Any]) -> str:
    """Serialize log record to JSON format following the spec."""
    import json

    extra = record["extra"]
    level_name = record["level"].name.lower()

    # Map loguru levels to spec levels
    level_map = {
        "trace": "debug",
        "debug": "debug",
        "info": "info",
        "success": "info",
        "warning": "warn",
        "error": "error",
        "critical": "fatal",
    }

    output: dict[str, Any] = {
        "level": level_map.get(level_name, level_name),
        "time": int(record["time"].timestamp() * 1000),
        "msg": record["message"],
        "service": extra.get("service", "unknown"),
    }

    # Add all extra fields (except internal ones)
    for key, value in extra.items():
        if key in ("service",):
            continue
        output[key] = value

    return json.dumps(output, ensure_ascii=False, default=str)


def _format_pretty(record: dict[str, Any]) -> str:
    """Format log record for development (pretty output)."""
    extra = record["extra"]
    timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S")
    level = record["level"].name.upper()
    msg = record["message"]

    lines = [f"[{timestamp}] {level}: {msg}"]

    for key, value in extra.items():
        if key == "error" and isinstance(value, dict):
            lines.append(f"    error.type: {value.get('type', 'Unknown')}")
            lines.append(f"    error.message: {value.get('message', '')}")
            if value.get("stack"):
                lines.append("    error.stack:")
                for stack_line in value["stack"].strip().split("\n"):
                    lines.append(f"        {stack_line}")
        else:
            lines.append(f"    {key}: {value}")

    return "\n".join(lines)


def _sink_json(message: Any) -> None:
    """Sink that outputs JSON to stderr."""
    serialized = _serialize(message.record)
    sys.stderr.write(serialized + "\n")


def _sink_pretty(message: Any) -> None:
    """Sink that outputs pretty format to stderr."""
    formatted = _format_pretty(message.record)
    sys.stderr.write(formatted + "\n")


class Logger:
    """Structured logger following Truley logging spec."""

    def __init__(
        self,
        level: LevelStr = "info",
        pretty: bool = False,
    ) -> None:
        from truley_python.tracing import get_service_name

        self.service = get_service_name() or "unknown"
        self._logger = _loguru_logger.bind(service=self.service)

        # Remove default handler and add custom one
        self._logger.remove()

        level_upper = level.upper()
        if level_upper == "WARN":
            level_upper = "WARNING"
        elif level_upper == "FATAL":
            level_upper = "CRITICAL"
        elif level_upper == "VERBOSE":
            level_upper = "DEBUG"

        sink = _sink_pretty if pretty else _sink_json
        self._logger.add(sink, level=level_upper, format="{message}")

    def _log(
        self,
        level: str,
        msg: str,
        error: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        # Auto-inject trace context if tracing is enabled
        from truley_python.tracing import get_current_trace_context, is_tracing_enabled

        trace_ctx = get_current_trace_context() if is_tracing_enabled() else None
        if trace_ctx:
            kwargs.setdefault("trace_id", trace_ctx["trace_id"])
            kwargs.setdefault("span_id", trace_ctx["span_id"])

        bound = self._logger.bind(**kwargs)

        if error is not None:
            bound = bound.bind(
                error={
                    "type": type(error).__name__,
                    "message": str(error),
                    "stack": "".join(
                        traceback.format_exception(
                            type(error), error, error.__traceback__
                        )
                    ),
                }
            )

        bound.log(level, msg)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log("DEBUG", msg, **kwargs)

    def verbose(self, msg: str, **kwargs: Any) -> None:
        self._log("DEBUG", msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log("INFO", msg, **kwargs)

    def warn(self, msg: str, **kwargs: Any) -> None:
        self._log("WARNING", msg, **kwargs)

    def error(
        self, msg: str, *, error: BaseException | None = None, **kwargs: Any
    ) -> None:
        self._log("ERROR", msg, error=error, **kwargs)

    def fatal(
        self, msg: str, *, error: BaseException | None = None, **kwargs: Any
    ) -> None:
        self._log("CRITICAL", msg, error=error, **kwargs)


def create_logger(
    level: LevelStr = "info",
    pretty: bool = False,
) -> Logger:
    """Create a structured logger.

    Service name is automatically taken from init_tracing().

    Args:
        level: Log level ("debug", "verbose", "info", "warn", "error", "fatal")
        pretty: Use pretty format for development (default: JSON)

    Returns:
        Logger instance

    Example:
        >>> from truley_python.tracing import init_tracing
        >>> init_tracing("http://localhost:4318", "backend")
        >>> logger = create_logger()
        >>> logger.info("Hello")
    """
    return Logger(level=level, pretty=pretty)


class InterceptHandler(logging.Handler):
    """Handler that intercepts stdlib logging and forwards to truley Logger."""

    def __init__(self, truley_logger: Logger) -> None:
        super().__init__()
        self.truley_logger = truley_logger

    def emit(self, record: logging.LogRecord) -> None:
        # Map stdlib levels to truley levels
        level_map = {
            logging.DEBUG: "debug",
            logging.INFO: "info",
            logging.WARNING: "warn",
            logging.ERROR: "error",
            logging.CRITICAL: "fatal",
        }

        level = level_map.get(record.levelno, "info")
        msg = record.getMessage()

        getattr(self.truley_logger, level)(
            msg,
            logger_name=record.name,
            module=record.module,
        )


def intercept_stdlib_logging(
    truley_logger: Logger, loggers: list[str] | None = None
) -> None:
    """Intercept stdlib logging and forward to truley logger.

    Args:
        truley_logger: The truley Logger instance to forward logs to
        loggers: List of logger names to intercept. If None, intercepts root logger.
                 Common values: ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]

    Example:
        >>> logger = create_logger()
        >>> intercept_stdlib_logging(logger, ["uvicorn", "uvicorn.access", "uvicorn.error"])
    """
    handler = InterceptHandler(truley_logger)

    if loggers is None:
        # Intercept root logger
        logging.root.handlers = [handler]
        logging.root.setLevel(logging.DEBUG)
    else:
        for name in loggers:
            stdlib_logger = logging.getLogger(name)
            stdlib_logger.handlers = [handler]
            stdlib_logger.setLevel(logging.DEBUG)
            stdlib_logger.propagate = False
