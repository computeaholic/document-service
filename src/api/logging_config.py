"""Logging configuration for the API."""

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log_record)


def configure_logging() -> None:
    """Configure application logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
