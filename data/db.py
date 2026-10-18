from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .base import Base
from .models import Record, Tag

engine = create_engine(
    "sqlite:///./Data/app.db", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    # Создаём новую сессию для одного HTTP-запроса
    session = SessionLocal()

    try:
        # Отдаём сессию туда, кто её запросил через Depends
        yield session
    finally:
        # После завершения запроса закрываем сессию
        session.close()


def create_record(session: Session, data: dict) -> Record:
    # Pydantic уже отдал правильный словарь, но копируем для безопасности
    data_copy = data.copy()
    tag_names = data_copy.pop("tags", [])

    # Находим или создаем теги
    tag_objects = []
    for name in tag_names:
        tag = session.query(Tag).filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            session.add(tag)
        tag_objects.append(tag)

    new_record = Record(**data_copy, tags=tag_objects)
    session.add(new_record)
    session.commit()
    session.refresh(new_record)
    return new_record


def update_record(session: Session, record_id: int, data: dict) -> Record | None:
    record = session.query(Record).filter(Record.id == record_id).first()
    if not record:
        return None

    data_copy = data.copy()
    tag_names = data_copy.pop("tags", None)

    # Обновляем обычные поля
    for key, value in data_copy.items():
        if hasattr(Record, key) and key != "id":
            setattr(record, key, value)

    # Обновляем теги, если они переданы
    if tag_names is not None:
        tag_objects = []
        for name in tag_names:
            tag = session.query(Tag).filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                session.add(tag)
            tag_objects.append(tag)
        record.tags = tag_objects

    session.commit()
    session.refresh(record)
    return record


def delete_record(session: Session, record_id: int) -> bool:
    # 1. Ищем запись
    record = session.query(Record).filter(Record.id == record_id).first()

    # 2. Если не нашли — возвращаем False
    if not record:
        return False

    # 3. Удаляем запись и связи из record_tag (теги остаются)
    session.delete(record)
    session.commit()

    return True


def delete_tag(session: Session, tag_name: str) -> bool:
    """
    Удаляет тег и все связи с записями.
    Возвращает True, если тег найден и удален, False иначе.
    """
    # 1. Ищем тег
    tag = session.query(Tag).filter_by(name=tag_name).first()
    if not tag:
        return False

    # 2. Разрываем все связи: удаляем тег из списка tags у каждой связанной записи
    for record in tag.records:
        record.tags.remove(tag)

    # 3. Теперь удаляем сам тег
    session.delete(tag)
    session.commit()

    return True


def get_record_by_id(session: Session, record_id: int) -> Record | None:
    record = session.query(Record).filter(Record.id == record_id).first()
    return record  # Вернет объект Record с загруженными tags или None


def get_records_by_tag(session: Session, tag_name: str) -> list[Record]:
    """Получить все записи с определенным тегом (для сортировки/фильтрации)"""
    tag = session.query(Tag).filter_by(name=tag_name).first()
    if not tag:
        return []
    return tag.records  # Благодаря backref='records' у тега есть список записей


def sync_tags(session: Session, desired_tag_names: list[str]) -> dict:
    """
    Синхронизирует теги в БД с желаемым списком.
    Возвращает словарь: {'added': [...], 'removed': [...], 'unchanged': [...]}
    """
    # 1. Получаем все текущие теги из БД
    current_tags = session.query(Tag).all()
    current_names = {tag.name for tag in current_tags}
    desired_set = set(desired_tag_names)

    # 2. Вычисляем разницу
    to_add = desired_set - current_names
    to_remove = current_names - desired_set
    unchanged = current_names & desired_set

    # 3. Добавляем новые теги
    added_tags = []
    for name in to_add:
        new_tag = Tag(name=name)
        session.add(new_tag)
        added_tags.append(name)

    # 4. Удаляем старые теги
    removed_tags = []
    for name in to_remove:
        tag = session.query(Tag).filter_by(name=name).first()
        if tag:
            # Проверяем, не используется ли тег
            if tag.records:
                # Если тег используется, не удаляем (или можно удалить связи)
                # Для простоты пропускаем
                continue
            session.delete(tag)
            removed_tags.append(name)

    # 5. Коммитим все изменения
    session.commit()

    return {"added": added_tags, "removed": removed_tags, "unchanged": list(unchanged)}


def get_records_paginated(
    session: Session, skip: int = 0, limit: int = 20
) -> list[Record]:
    """
    Возвращает список записей с пагинацией.
    skip: сколько записей пропустить (offset)
    limit: сколько записей вернуть
    """
    records = (
        session.query(Record)
        .order_by(Record.created_at.desc())  # Сортировка обязательна!
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records
