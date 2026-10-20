"""Экспорт и импорт записей в JSON (ТЗ, раздел 7)."""
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from core import settings
from data import taxonomy
from data.models import (
    Category,
    Record,
    Tag,
    record_prerequisite,
    record_related,
)
from utils.images import delete_image_files
from utils.text import build_search_text, sanitize_html

SCHEMA_VERSION = 1


class RecordExport(BaseModel):
    """Единственное место, где задан состав полей выгрузки (ТЗ, 7.2).

    Новое текстовое поле: колонка в модели + поле в форме + строка здесь.
    """

    id: int
    title: str
    category: str
    is_published: bool = True
    created_at: datetime | None = None
    description: str = ""
    text: str = ""
    tags: list[str] = []
    related: list[int] = []
    requires: list[int] = []
    video_url: str | None = None


class ExportFile(BaseModel):
    schema_version: int = SCHEMA_VERSION
    exported_at: str | None = None
    records: list[RecordExport]


class ImportReport(BaseModel):
    added: int = 0
    updated: int = 0
    skipped: int = 0
    warnings: list[str] = []

    def summary(self) -> str:
        return f"добавлено {self.added}, обновлено {self.updated}, пропущено {self.skipped}"


class ImportFailed(Exception):
    """Файл не прошёл проверку; в базе ничего не изменено."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def export_data(session: Session) -> dict:
    related: dict[int, set[int]] = {}
    for a, b in session.execute(record_related.select()).all():
        related.setdefault(a, set()).add(b)
        related.setdefault(b, set()).add(a)  # связь симметрична
    requires: dict[int, set[int]] = {}
    for rid, req in session.execute(record_prerequisite.select()).all():
        requires.setdefault(rid, set()).add(req)

    items = []
    for record in session.query(Record).order_by(Record.id):
        items.append(
            RecordExport(
                id=record.id,
                title=record.title,
                category=record.category.name,
                is_published=record.is_published,
                created_at=record.created_at,
                description=record.description,
                text=record.text,
                tags=[t.name for t in record.tags],
                related=sorted(related.get(record.id, ())),
                requires=sorted(requires.get(record.id, ())),
                video_url=record.video_url if settings.VIDEO_ENABLED else None,
            ).model_dump(mode="json", exclude_none=True)
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "records": items,
    }


def _parse(payload: dict) -> tuple[ExportFile, list[str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ImportFailed(["Ожидается JSON с полем records (список записей)"])
    warnings: list[str] = []
    known = set(RecordExport.model_fields)
    problems: list[str] = []
    for index, raw in enumerate(payload["records"], start=1):
        if not isinstance(raw, dict):
            problems.append(f"Запись №{index}: ожидается объект")
            continue
        extra = set(raw) - known
        if extra:
            warnings.append(
                f"Запись №{index}: неизвестные поля проигнорированы: {', '.join(sorted(extra))}"
            )
        try:
            RecordExport.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                place = ".".join(str(p) for p in err["loc"])
                problems.append(f"Запись №{index} (id={raw.get('id')}): {place}: {err['msg']}")
    if problems:
        raise ImportFailed(problems)
    version = payload.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, int) and version > SCHEMA_VERSION:
        warnings.append(f"Файл новее программы (версия {version}), часть полей могла быть пропущена")
    return ExportFile.model_validate(payload), warnings


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def import_data(session: Session, payload: dict, replace: bool = False) -> ImportReport:
    """Добавляет и обновляет записи (по id). Всё или ничего.

    replace=True сначала удаляет все записи, теги и категории: только для терминала.
    """
    parsed, warnings = _parse(payload)
    report = ImportReport(warnings=warnings)
    files_to_delete: list[str] = []
    try:
        if replace:
            for record in session.query(Record):
                files_to_delete += [i.filename for i in record.images]
            session.execute(delete(Record))
            session.execute(delete(Tag))
            session.execute(delete(Category))
            session.expire_all()

        seen: set[int] = set()
        for item in parsed.records:
            if item.id in seen:
                report.skipped += 1
                report.warnings.append(f"id={item.id}: повтор в файле, пропущено")
                continue
            seen.add(item.id)
            # Категория и теги создаются до записи: иначе автосброс увидит запись без категории
            category = taxonomy.get_or_create_category(session, item.category)
            tags = [taxonomy.get_or_create_tag(session, name) for name in item.tags]
            record = session.get(Record, item.id)
            is_new = record is None
            if is_new:
                record = Record(id=item.id, category=category)
                session.add(record)
            record.category = category
            record.tags = tags
            record.title = item.title.strip()
            record.description = item.description.strip()
            record.text = sanitize_html(item.text)  # импорт не обход очистки (ТЗ 2.7)
            record.is_published = item.is_published
            record.search_text = build_search_text(record.title, record.description)
            if settings.VIDEO_ENABLED and item.video_url is not None:
                record.video_url = item.video_url
            if item.created_at:
                record.created_at = _naive_utc(item.created_at)
            report.added += is_new
            report.updated += not is_new
        session.flush()

        _restore_relations(session, parsed.records, seen, report)
        session.commit()
    except Exception:
        session.rollback()
        raise
    delete_image_files(files_to_delete)
    return report


def _restore_relations(session, items, ids: set[int], report: ImportReport) -> None:
    """Второй проход: связи восстанавливаются, когда все записи уже созданы."""
    for item in items:
        if item.id not in ids:
            continue
        session.execute(delete(record_prerequisite).where(record_prerequisite.c.record_id == item.id))
        session.execute(
            delete(record_related).where(
                (record_related.c.record_id == item.id)
                | (record_related.c.related_id == item.id)
            )
        )
    existing = {rid for (rid,) in session.query(Record.id)}
    pairs: set[tuple[int, int]] = set()
    required: set[tuple[int, int]] = set()
    for item in items:
        if item.id not in ids:
            continue
        for other in item.related:
            if other == item.id or other not in existing:
                report.warnings.append(f"id={item.id}: связь с {other} пропущена")
                continue
            pairs.add((min(item.id, other), max(item.id, other)))
        for other in item.requires:
            if other == item.id or other not in existing:
                report.warnings.append(f"id={item.id}: «сначала освой» {other} пропущено")
                continue
            required.add((item.id, other))
    if pairs:
        session.execute(
            insert(record_related),
            [{"record_id": a, "related_id": b} for a, b in sorted(pairs)],
        )
    if required:
        session.execute(
            insert(record_prerequisite),
            [{"record_id": a, "requires_id": b} for a, b in sorted(required)],
        )
