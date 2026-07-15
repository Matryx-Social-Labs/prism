"""Structured logging for every Prism process (api, worker, scripts).

Production (Railway) emits JSON lines — Railway parses them into
filterable attributes, so log analysis becomes queries like
`event=item_classified stage=classification` instead of grepping prose.
Dev TTYs get pretty console rendering. Stdlib logging is routed through
structlog so third-party libraries land in the same format.

Usage:
    from common.logging import get_logger, setup_logging
    setup_logging()                      # once, at process start
    log = get_logger(__name__)
    log.info("item_classified", stage="classification", raw_item_id=str(id))
"""

import logging
import os
import sys

import structlog


def setup_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    # JSON in production; pretty console when attached to a TTY (local dev).
    # Railway sets RAILWAY_ENVIRONMENT; LOG_FORMAT=json|console overrides.
    fmt = os.environ.get(
        "LOG_FORMAT",
        "console" if sys.stderr.isatty() and not os.environ.get("RAILWAY_ENVIRONMENT") else "json",
    )

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer = (
        structlog.dev.ConsoleRenderer()
        if fmt == "console"
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Noise control: transient Langfuse-export retries flooded logs; uvicorn
    # access lines duplicate what the JSON request logs already carry.
    logging.getLogger("opentelemetry").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
