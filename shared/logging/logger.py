"""
SentinelOS — Structured Logging

Every log line is JSON with consistent fields.
In production, these feed into log aggregators (Datadog, Loki, CloudWatch).
In development, they render as readable colored output.

Key pattern: bind context (correlation_id, run_id) once,
then every subsequent log call in that context carries those fields
automatically — no manual repetition.

Usage:
    from shared.logging.logger import get_logger, bind_context

    logger = get_logger(__name__)
    logger.info("event_appended", event_id=str(event_id), run_id=str(run_id))

    # Bind context for the duration of a request
    with bind_context(correlation_id="abc-123", run_id="run-456"):
        logger.info("processing_started")   # automatically includes context
        logger.info("processing_complete")  # automatically includes context
"""

import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from shared.config.settings import get_settings


def _add_service_name(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject the service name into every log event."""
    settings = get_settings()
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["env"] = settings.app_env
    return event_dict


def _drop_color_message_key(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Uvicorn emits a 'color_message' key alongside 'message'.
    Remove it so our JSON logs stay clean.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the entire application.

    Call this exactly once at application startup (in main.py).
    Configures both structlog and the stdlib logging module
    so third-party libraries (SQLAlchemy, aiokafka) also
    emit structured output.
    """
    settings = get_settings()

    shared_processors: list[Processor] = [
        # Add log level string
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add service context
        _add_service_name,
        # Remove uvicorn color keys
        _drop_color_message_key,
        # Render exceptions cleanly
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_development:
        # Human-readable colored output in development
        processors: list[Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Machine-parseable JSON in staging/production
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so uvicorn, sqlalchemy, aiokafka
    # emit through our structured pipeline
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )

    # Silence noisy libraries in development
    if settings.is_development:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("aiokafka").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structured logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger that can be extended with
        .bind() to add persistent context fields.

    Example:
        logger = get_logger(__name__)
        logger = logger.bind(run_id="abc-123")
        logger.info("event_appended", event_type="TOOL_CALLED")
    """
    return structlog.get_logger(name)  # type: ignore[return-value]


@contextmanager
def bind_context(**kwargs: Any) -> Generator[None, None, None]:
    """
    Context manager that binds key-value pairs to all log calls
    within the block, then cleans up on exit.

    This is used at request boundaries (middleware) to inject
    correlation_id and run_id into every log line automatically.

    Example:
        with bind_context(correlation_id="abc", run_id="xyz"):
            logger.info("step_one")   # includes correlation_id + run_id
            logger.info("step_two")   # includes correlation_id + run_id
        # Context cleared after the block
    """
    structlog.contextvars.bind_contextvars(**kwargs)
    try:
        yield
    finally:
        structlog.contextvars.unbind_contextvars(*kwargs.keys())


def bind_request_context(
    correlation_id: str,
    run_id: str | None = None,
) -> None:
    """
    Bind request-scoped context for the duration of an async request.

    Called by the logging middleware at the start of each HTTP request.
    Uses structlog's async-safe contextvars (not thread-local).
    """
    context: dict[str, str] = {"correlation_id": correlation_id}
    if run_id:
        context["run_id"] = run_id
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context() -> None:
    """Clear all bound context variables. Called at request end."""
    structlog.contextvars.clear_contextvars()
