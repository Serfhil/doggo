"""Теги и категории: создание, переименование, удаление, объединение."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.models import Category, Record, Tag, record_tag
from data.schemas import check_name
from utils.text import normalize_key


class TaxonomyError(Exception):
    """Понятная пользователю ошибка (показывается на странице)."""


def _validated(model, session: Session, name: str, exclude_id: int | None = None):
    name, error = check_name(name)
    if error:
        raise TaxonomyError(error)
    key = normalize_key(name)
    query = session.query(model).filter(model.name_key == key)
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    if query.first():
        raise TaxonomyError(f"«{name}» уже есть")
    return name, key


def tags_with_counts(session: Session) -> list[tuple[Tag, int]]:
    rows = (
        session.query(Tag, func.count(record_tag.c.record_id))
        .outerjoin(record_tag, record_tag.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.name_key)
        .all()
    )
    return [(tag, count) for tag, count in rows]


def categories_with_counts(session: Session) -> list[tuple[Category, int]]:
    rows = (
        session.query(Category, func.count(Record.id))
        .outerjoin(Record, Record.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.id)  # порядок создания
        .all()
    )
    return [(cat, count) for cat, count in rows]


def all_categories(session: Session) -> list[Category]:
    return session.query(Category).order_by(Category.id).all()


def all_tags(session: Session) -> list[Tag]:
    return session.query(Tag).order_by(Tag.name_key).all()


def get_or_create_tag(session: Session, name: str) -> Tag:
    """Тег по имени без учёта регистра; нового создаёт. Коммит делает вызывающий."""
    name, error = check_name(name)
    if error:
        raise TaxonomyError(error)
    key = normalize_key(name)
    tag = session.query(Tag).filter(Tag.name_key == key).first()
    if not tag:
        tag = Tag(name=name, name_key=key)
        session.add(tag)
        session.flush()
    return tag


def get_or_create_category(session: Session, name: str) -> Category:
    name, error = check_name(name)
    if error:
        raise TaxonomyError(error)
    key = normalize_key(name)
    cat = session.query(Category).filter(Category.name_key == key).first()
    if not cat:
        cat = Category(name=name, name_key=key)
        session.add(cat)
        session.flush()
    return cat


def add_tag(session: Session, name: str) -> Tag:
    name, key = _validated(Tag, session, name)
    tag = Tag(name=name, name_key=key)
    session.add(tag)
    session.commit()
    return tag


def add_category(session: Session, name: str) -> Category:
    name, key = _validated(Category, session, name)
    cat = Category(name=name, name_key=key)
    session.add(cat)
    session.commit()
    return cat


def rename(session: Session, model, item_id: int, name: str) -> None:
    item = session.get(model, item_id)
    if not item:
        raise TaxonomyError("Не найдено")
    name, key = _validated(model, session, name, exclude_id=item_id)
    item.name, item.name_key = name, key
    session.commit()


def delete_tag(session: Session, tag_id: int) -> None:
    tag = session.get(Tag, tag_id)
    if not tag:
        raise TaxonomyError("Тег не найден")
    session.delete(tag)  # связи с записями удаляются вместе с ним
    session.commit()


def merge_tags(session: Session, source_id: int, target_id: int) -> None:
    """Все записи с тегом source получают target, source удаляется."""
    if source_id == target_id:
        raise TaxonomyError("Выберите другой тег")
    source, target = session.get(Tag, source_id), session.get(Tag, target_id)
    if not source or not target:
        raise TaxonomyError("Тег не найден")
    for record in list(source.records):
        if target not in record.tags:
            record.tags.append(target)
    session.flush()
    session.delete(source)
    session.commit()


def delete_category(session: Session, category_id: int) -> None:
    cat = session.get(Category, category_id)
    if not cat:
        raise TaxonomyError("Категория не найдена")
    used = session.query(Record).filter(Record.category_id == category_id).count()
    if used:
        raise TaxonomyError(
            f"Категория «{cat.name}» используется в записях: {used}. "
            "Сначала перенесите их в другую категорию"
        )
    session.delete(cat)
    session.commit()


def move_category_records(session: Session, source_id: int, target_id: int) -> int:
    if source_id == target_id:
        raise TaxonomyError("Выберите другую категорию")
    if not session.get(Category, source_id) or not session.get(Category, target_id):
        raise TaxonomyError("Категория не найдена")
    moved = (
        session.query(Record)
        .filter(Record.category_id == source_id)
        .update({Record.category_id: target_id})
    )
    session.commit()
    return moved
