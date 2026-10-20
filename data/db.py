from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core import settings
from data.base import Base
from data.models import Category, Tag
from utils.logger import get_logger
from utils.text import normalize_key

logger = get_logger(__name__)

DEFAULT_CATEGORIES = ["команда", "упражнение", "игра", "игрушка"]
DEFAULT_TAGS = ["Лёгкий", "Средний", "Тяжёлый"]


def _enable_sqlite_pragmas(dbapi_connection, _record):
    # Внешние ключи в SQLite по умолчанию выключены; WAL нужен для чтения во время записи
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(url: str | None = None):
    if url is None:
        settings.database_file.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{settings.database_file}"
    kwargs = {"connect_args": {"check_same_thread": False}}
    if url == "sqlite://":
        # БД в памяти (тесты): одно соединение на всех, иначе у каждого будет своя пустая БД
        kwargs["poolclass"] = StaticPool
    eng = create_engine(url, **kwargs)
    event.listen(eng, "connect", _enable_sqlite_pragmas)
    return eng


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def seed_defaults(session: Session) -> None:
    """Предустановленные категории и теги: только в пустой базе."""
    if session.query(Category).count() == 0:
        for name in DEFAULT_CATEGORIES:
            session.add(Category(name=name, name_key=normalize_key(name)))
    if session.query(Tag).count() == 0:
        for name in DEFAULT_TAGS:
            session.add(Tag(name=name, name_key=normalize_key(name)))
    session.commit()


def init_db(eng=None, factory=None) -> None:
    eng = eng or engine
    factory = factory or SessionLocal
    Base.metadata.create_all(bind=eng)
    with factory() as session:
        seed_defaults(session)


def get_db():
    # Новая сессия на один HTTP-запрос
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
