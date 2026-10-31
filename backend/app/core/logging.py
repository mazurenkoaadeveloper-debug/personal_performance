import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = ("authorization", "token")


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED
                if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
                else _redact(nested_value)
            )
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def redact_secrets(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    return dict(_redact(event_dict))


def configure_logging() -> None:
    logging.basicConfig(stream=sys.stdout, format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_secrets,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
