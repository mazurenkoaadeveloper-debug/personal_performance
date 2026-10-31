import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog
from pydantic import SecretStr


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = ("authorization", "token")
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?P<prefix>(?:access[_-]?token|private[_-]?token|authorization|token)=)"
    r"(?P<value>[^&\s\"']+)",
    flags=re.IGNORECASE,
)


def _redact(value: Any, key: str | None = None) -> Any:
    if key and any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
        return REDACTED
    if isinstance(value, SecretStr):
        return REDACTED
    if isinstance(value, str):
        return SENSITIVE_VALUE_PATTERN.sub(
            lambda match: f"{match.group('prefix')}{REDACTED}",
            value,
        )
    if isinstance(value, Mapping):
        return {
            nested_key: _redact(nested_value, str(nested_key))
            for nested_key, nested_value in value.items()
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
    timestamp = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamp,
    ]

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            *shared_processors,
            redact_secrets,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            redact_secrets,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)
