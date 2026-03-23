"""
Configure structlog for JSON (or console) output. Call configure_logging() at app startup.
"""

import sys

import structlog


def configure_logging(json_logs: bool = True) -> None:
    """Configure structlog. Set json_logs=False for dev-friendly console output."""
    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if json_logs:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
