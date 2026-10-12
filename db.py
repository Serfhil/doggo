# db.py
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from sqlalchemy import JSON, String
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Локальный .env удобен для разработки.
# В продакшене переменные обычно приходят из окружения контейнера/сервера.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "app.db"

# Для SQLite путь абсолютный, чтобы файл создавался рядом с проектом,
# независимо от текущей рабочей директории запуска.
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH.as_posix()}"

# Смена СУБД сводится к изменению DATABASE_URL и установки драйвера.
# Например: postgresql+asyncpg://user:password@localhost:5432/database
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

TITLE_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 1000
TAG_MAX_LENGTH = 50

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    # После commit объекты остаются пригодными для чтения в том же запросе.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), index=True)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_MAX_LENGTH))
    # JSON-колонка упрощает старт: не нужны связи и отдельные запросы для тегов.
    # Минус: сложный поиск по тегам будет медленнее, чем в нормализованной схеме.
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)


async def init_db() -> None:
    """Создаёт отсутствующие таблицы. Существующие данные не удаляет."""
    async with engine.begin() as conn:
        # create_all — синхронный API метаданных, поэтому вызываем через run_sync.
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Освобождает соединения в пуле движка."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: открыть сессию, отдать её обработчику и закрыть после запроса."""
    async with async_session_factory() as session:
        yield session
