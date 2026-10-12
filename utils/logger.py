# utils/logger.py
import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_configured = False


def setup_logging(level: Optional[str] = None) -> None:
    """Настраивает корневой логгер один раз за процесс."""
    global _configured
    if _configured:
        return

    resolved_level = (level or _DEFAULT_LEVEL).upper()
    logging.basicConfig(
        level=resolved_level,
        format=_LOG_FORMAT,
    )

    # Не засоряем вывод служебными сообщениями, если они не нужны для отладки.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Возвращает именованный логгер и гарантирует, что logging настроен."""
    setup_logging()
    return logging.getLogger(name)
