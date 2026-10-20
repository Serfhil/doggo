from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Промежуточная таблица тегов: составной первичный ключ запрещает дубли связи
record_tag = Table(
    "record_tag",
    Base.metadata,
    Column(
        "record_id",
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    ),
)

# «Связанные записи». Пара хранится один раз (record_id < related_id), читается в обе стороны
record_related = Table(
    "record_related",
    Base.metadata,
    Column(
        "record_id",
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "related_id",
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# «Сначала освой»: record_id требует предварительно освоить requires_id
record_prerequisite = Table(
    "record_prerequisite",
    Base.metadata,
    Column(
        "record_id",
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "requires_id",
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # Название в нормализованном виде (casefold, ё->е): по нему проверяем уникальность
    name_key = Column(String, nullable=False, unique=True)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    name_key = Column(String, nullable=False, unique=True)


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True)
    record_id = Column(
        Integer, ForeignKey("records.id", ondelete="CASCADE"), nullable=False
    )
    filename = Column(String, nullable=False)  # <uuid>.webp, миниатюра <uuid>_thumb.webp
    alt = Column(String, nullable=False, default="")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow)

    @property
    def thumb_filename(self) -> str:
        return self.filename.replace(".webp", "_thumb.webp")


class Record(Base):
    __tablename__ = "records"
    # AUTOINCREMENT: номер удалённой записи не выдаётся повторно
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    # Название + описание в нормализованном виде, по нему идёт поиск
    search_text = Column(String, nullable=False, default="")
    text = Column(Text, nullable=False, default="")  # очищенный HTML
    category_id = Column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    video_url = Column(String)
    views = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("Category", lazy="joined")
    # selectin: теги загружаются сразу одним запросом
    tags = relationship(
        "Tag", secondary=record_tag, backref="records", lazy="selectin",
        order_by="Tag.name_key",
    )
    images = relationship(
        "Image",
        order_by="Image.position",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DailyVisits(Base):
    __tablename__ = "daily_visits"
    day = Column(Date, primary_key=True, default=date.today)
    views = Column(Integer, nullable=False, default=0)
