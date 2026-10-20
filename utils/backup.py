"""Копия файла SQLite (безопасно, пока база используется)."""
import sqlite3
from datetime import datetime
from pathlib import Path

from core import BASE_DIR, settings
from utils.logger import get_logger

logger = get_logger(__name__)

BACKUP_DIR = BASE_DIR / "backups"


def backup_database(prefix: str = "app", keep: int = 10) -> Path | None:
    """Копирует БД в backups/<prefix>-<время>.db, хранит последние keep копий с этим префиксом."""
    source = settings.database_file
    if not source.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / f"{prefix}-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
    src, dst = sqlite3.connect(source), sqlite3.connect(target)
    try:
        src.backup(dst)  # согласованная копия, в отличие от обычного cp
    finally:
        dst.close()
        src.close()
    for old in sorted(BACKUP_DIR.glob(f"{prefix}-*.db"))[:-keep]:
        old.unlink(missing_ok=True)
    logger.info("Database backup created: %s", target.name)
    return target
