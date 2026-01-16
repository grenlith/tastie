import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, TextIO

_original_stderr: TextIO = sys.stderr
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", "") or request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        for key in ("user_id", "bookmark_id", "operation", "duration_ms", "status_code", "path"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def setup_logging(log_file: str, log_level: str, json_format: bool = False) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    if json_format:
        formatter: logging.Formatter = JSONFormatter()
    else:
        format_str = "%(asctime)s [%(request_id)s] %(name)s %(levelname)s - %(message)s"
        formatter = logging.Formatter(format_str)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []

    request_filter = RequestIDFilter()

    stream_handler = logging.StreamHandler(_original_stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(request_filter)
    root_logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        root_logger.addHandler(file_handler)

        for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            uvi_logger = logging.getLogger(logger_name)
            uvi_logger.addHandler(file_handler)
            uvi_logger.propagate = False

        # watchfiles writes to log file and causes infinite reload loop
        watchfiles_logger = logging.getLogger("watchfiles")
        watchfiles_logger.handlers = [stream_handler]
        watchfiles_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
