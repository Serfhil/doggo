"""Запросы и изменения записей."""
from sqlalchemy.orm import Session

from data import taxonomy
from data.models import Record, Tag
from data.schemas import RecordForm
from utils.images import delete_image_files
from utils.logger import get_logger
from utils.text import build_search_text, normalize_key

logger = get_logger(__name__)


def get_record(session: Session, record_id: int) -> Record | None:
    return session.get(Record, record_id)


def _filtered(
    session: Session,
    *,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str = "",
    published_only: bool = True,
    status: str = "",
):
    query = session.query(Record)
    if published_only:
        query = query.filter(Record.is_published.is_(True))
    elif status == "published":
        query = query.filter(Record.is_published.is_(True))
    elif status == "draft":
        query = query.filter(Record.is_published.is_(False))
    if category_id:
        query = query.filter(Record.category_id == category_id)
    if tag_id:
        query = query.filter(Record.tags.any(Tag.id == tag_id))
    key = normalize_key(q or "")
    if key:
        query = query.filter(Record.search_text.contains(key, autoescape=True))
    return query


def list_records(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 12,
    **filters,
) -> tuple[list[Record], int]:
    """Страница записей (новые первыми) и общее число найденных."""
    query = _filtered(session, **filters)
    total = query.count()
    items = (
        query.order_by(Record.created_at.desc(), Record.id.desc())
        .offset((max(page, 1) - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def _apply_tags(session: Session, record: Record, tag_ids: list[int], new_names: str):
    tags: dict[int, Tag] = {}
    if tag_ids:
        for tag in session.query(Tag).filter(Tag.id.in_(tag_ids)).all():
            tags[tag.id] = tag
    for name in new_names.split(","):
        if name.strip():
            tag = taxonomy.get_or_create_tag(session, name)
            tags[tag.id] = tag
    record.tags = list(tags.values())


def save_record(
    session: Session,
    record: Record | None,
    form: RecordForm,
    tag_ids: list[int],
    new_tags: str = "",
) -> Record:
    """Создаёт запись или обновляет существующую. Данные формы уже проверены."""
    if record is None:
        record = Record()
        session.add(record)
    record.title = form.title
    record.description = form.description
    record.text = form.text
    record.category_id = form.category_id
    record.is_published = form.is_published
    record.search_text = build_search_text(form.title, form.description)
    _apply_tags(session, record, tag_ids, new_tags)
    session.commit()
    session.refresh(record)
    logger.info("Record %s saved", record.id)
    return record


def delete_record(session: Session, record_id: int) -> bool:
    record = session.get(Record, record_id)
    if not record:
        return False
    files = [image.filename for image in record.images]
    session.delete(record)
    session.commit()
    # Файлы удаляем после commit: сбой оставит лишний файл, но не битую ссылку (ТЗ 2.7)
    delete_image_files(files)
    return True
