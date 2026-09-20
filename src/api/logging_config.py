"""Logging configuration for the API."""

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Include extra fields from LoggerAdapter and extra kwargs
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
            ]:
                log_record[key] = value

        return json.dumps(log_record)


def configure_logging() -> None:
    """Configure application logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name("document_service_json")
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [
        existing_handler
        for existing_handler in root.handlers
        if existing_handler.get_name() != "document_service_json"
    ]
    root.addHandler(handler)
