# core.py
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi.templating import Jinja2Templates
from utils.text import excerpt
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# 1. Настройки приложения (читаются из .env)
# ==========================================
class Settings(BaseSettings):
    SITE_NAME: str = "Тренируем собачку"
    SITE_URL: str = "http://127.0.0.1:8000"
    SITE_TIMEZONE: str = "Europe/Moscow"
    # Относительные пути считаются от корня проекта
    DATABASE_PATH: str = "data/app.db"
    UPLOAD_DIR: str = "uploads"
    VIDEO_ENABLED: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Лимиты картинок (ТЗ, раздел 4)
    MAX_UPLOAD_MB: int = 10
    MAX_IMAGES_PER_RECORD: int = 10
    PAGE_SIZE: int = 12

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def database_file(self) -> Path:
        path = Path(self.DATABASE_PATH)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        return path if path.is_absolute() else BASE_DIR / path


settings = Settings()

# ==========================================
# 2. Шаблоны и общие объекты
# ==========================================
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

try:
    _tz = ZoneInfo(settings.SITE_TIMEZONE)
except ZoneInfoNotFoundError:
    _tz = timezone.utc


def local_dt(value: datetime | None) -> datetime | None:
    """Время из БД (UTC, без пояса) -> время сайта."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_tz)


def format_date(value: datetime | None) -> str:
    local = local_dt(value)
    return local.strftime("%d.%m.%Y") if local else ""


def format_datetime(value: datetime | None) -> str:
    local = local_dt(value)
    return local.strftime("%d.%m.%Y %H:%M") if local else ""




def summary(record) -> str:
    """Краткое описание карточки: своё или начало текста (ТЗ 3.4)."""
    return record.description or excerpt(record.text)


templates.env.globals["summary"] = summary
templates.env.filters["date"] = format_date
templates.env.filters["datetime"] = format_datetime
templates.env.globals["settings"] = settings
