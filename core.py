# core.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# 1. Настройки приложения (бывший config.py)
# ==========================================
class Settings(BaseSettings):
    ADMIN_MODE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Экземпляр настроек для импорта
settings = Settings()

# ==========================================
# 2. Шаблоны и общие объекты
# ==========================================
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
