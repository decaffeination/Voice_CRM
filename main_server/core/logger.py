import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.context import request_id_var, session_id_var, user_id_var


class ContextFilter(logging.Filter):
    """把请求上下文（request_id/user_id/session_id）注入每条日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.session_id = session_id_var.get()
        return True


def setup_logger(name: str = "voice_crm") -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | "
        "rid=%(request_id)s uid=%(user_id)s sid=%(session_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    context_filter = ContextFilter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    logger.addHandler(console_handler)

    log_file: Path = settings.logging.abs_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
