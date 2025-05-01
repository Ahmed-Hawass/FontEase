"""
Logger module for application events and debugging.
"""

import logging
import logging.handlers
import json
import os
import threading
from typing import Optional, Any, Dict

class ContextFilter(logging.Filter):
    def filter(self, record):
        # Add thread name and any other contextual information
        record.threadName = threading.current_thread().name
        return True

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'thread': getattr(record, 'threadName', record.threadName),
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        if hasattr(record, 'extra_context'):
            log_record.update(record.extra_context)
        return json.dumps(log_record, ensure_ascii=False)

class AppLogger:
    """
    Application logger using Python's standard logging module.
    Logs to both console (human-readable) and file (JSON), supports rotation and contextual info.
    """
    def __init__(self, log_file: Optional[str] = None, log_level: Optional[str] = None):
        if not log_file:
            log_file = os.path.join(os.getenv('APPDATA'), 'FontEase', 'logs', 'fontease.log')
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        else:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger("fontease")
        self.logger.setLevel(getattr(logging, (log_level or os.getenv('FONTEASE_LOG_LEVEL', 'INFO')).upper()))
        self.logger.handlers.clear()
        self.logger.propagate = False
        self.logger.addFilter(ContextFilter())

        # Console handler (human-readable)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s][%(threadName)s][%(module)s:%(funcName)s:%(lineno)d] %(message)s'))
        self.logger.addHandler(ch)

        # File handler (JSON, rotation)
        if log_file:
            fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(JsonFormatter())
            self.logger.addHandler(fh)

    def set_level(self, level: str):
        self.logger.setLevel(getattr(logging, level.upper()))

    def info(self, message: str, extra_context: Optional[Dict[str, Any]] = None):
        self.logger.info(message, extra={'extra_context': extra_context or {}})

    def debug(self, message: str, extra_context: Optional[Dict[str, Any]] = None):
        self.logger.debug(message, extra={'extra_context': extra_context or {}})

    def warning(self, message: str, extra_context: Optional[Dict[str, Any]] = None):
        self.logger.warning(message, extra={'extra_context': extra_context or {}})

    def error(self, message: str, exc_info: Any = None, extra_context: Optional[Dict[str, Any]] = None):
        self.logger.error(message, exc_info=exc_info, extra={'extra_context': extra_context or {}})

    def critical(self, message: str, exc_info: Any = None, extra_context: Optional[Dict[str, Any]] = None):
        self.logger.critical(message, exc_info=exc_info, extra={'extra_context': extra_context or {}})

    def performance(self, operation: str, duration_ms: float, extra_context: Optional[Dict[str, Any]] = None):
        ctx = extra_context or {}
        ctx['operation'] = operation
        ctx['duration_ms'] = duration_ms
        self.logger.info(f"Performance: {operation} took {duration_ms:.2f}ms", extra={'extra_context': ctx})

    def usage(self, event: str, details: Optional[Dict[str, Any]] = None):
        ctx = details or {}
        ctx['usage_event'] = event
        self.logger.info(f"Usage event: {event}", extra={'extra_context': ctx})