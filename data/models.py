from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base

# Промежуточная таблица для связи Many-to-Many
record_tag = Table(
    "record_tag",
    Base.metadata,
    Column("record_id", Integer, ForeignKey("records.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    record_type = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    text = Column(Text)
    author = Column(String)

    # Связь с тегами: lazy='selectin' загружает теги сразу одним запросом
    tags = relationship("Tag", secondary=record_tag, backref="records", lazy="selectin")
