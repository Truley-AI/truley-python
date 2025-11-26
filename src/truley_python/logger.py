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
        service: str,
        level: LevelStr = "info",
        pretty: bool = False,
    ) -> None:
        self.service = service
        self._logger = _loguru_logger.bind(service=service)

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
    service: str,
    level: LevelStr = "info",
    pretty: bool = False,
) -> Logger:
    """Create a structured logger for a service.

    Args:
        service: Service name (e.g., "backend", "analyzer")
        level: Log level ("debug", "verbose", "info", "warn", "error", "fatal")
        pretty: Use pretty format for development (default: JSON)

    Returns:
        Logger instance

    Example:
        >>> logger = create_logger("backend")
        >>> logger.info("Meeting created", tenantId="t-123", meetingId="m-456")
        {"level":"info","time":1700000000000,"msg":"Meeting created","service":"backend","tenantId":"t-123","meetingId":"m-456"}
    """
    return Logger(service=service, level=level, pretty=pretty)
