# core.py
from pathlib import Path
from typing import Iterable, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.templating import Jinja2Templates
import db

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# 1. Настройки приложения (бывший config.py)
# ==========================================
class Settings(BaseSettings):
    ADMIN_MODE: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite+aiosqlite:///./my_database.db"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Экземпляр настроек для импорта
settings = Settings()

# ==========================================
# 2. Шаблоны и общие объекты
# ==========================================
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ==========================================
# 3. Вспомогательные функции (хелперы)
# ==========================================
def _collect_unique_tags(cards: Iterable[db.Card]) -> List[str]:
    tags: set[str] = set()
    for card in cards:
        tags.update(card.tags or [])
    return sorted(tags)


def _normalize_tags(raw_tags: List[str]) -> List[str]:
    tags: set[str] = set()
    for raw_tag in raw_tags:
        for tag in raw_tag.split(","):
            cleaned = tag.strip()
            if cleaned:
                tags.add(cleaned)
    return sorted(tags)
