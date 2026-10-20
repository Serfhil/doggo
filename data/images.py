"""Картинки записи: добавление, подпись, порядок, удаление."""
from sqlalchemy.orm import Session

from core import settings
from data.models import Image, Record
from utils.images import ImageError, delete_image_files, process_upload

ALT_MAX = 200


def image_dict(image: Image) -> dict:
    return {
        "id": image.id,
        "url": f"/uploads/{image.filename}",
        "thumb_url": f"/uploads/{image.thumb_filename}",
        "alt": image.alt,
        "position": image.position,
    }


def add_image(session: Session, record: Record, data: bytes) -> Image:
    if len(record.images) >= settings.MAX_IMAGES_PER_RECORD:
        raise ImageError(f"Не больше {settings.MAX_IMAGES_PER_RECORD} картинок на запись")
    filename = process_upload(data)
    try:
        image = Image(
            record_id=record.id, filename=filename, position=len(record.images)
        )
        session.add(image)
        session.commit()
    except Exception:
        session.rollback()
        delete_image_files([filename])
        raise
    return image


def set_alt(session: Session, image: Image, alt: str) -> Image:
    image.alt = " ".join(alt.split())[:ALT_MAX]
    session.commit()
    return image


def reorder(session: Session, record: Record, ids: list[int]) -> None:
    current = {image.id: image for image in record.images}
    if sorted(ids) != sorted(current):
        raise ImageError("Список картинок устарел, обновите страницу")
    for position, image_id in enumerate(ids):
        current[image_id].position = position
    session.commit()
    session.expire(record, ["images"])  # перечитать в новом порядке


def delete_image(session: Session, image: Image) -> None:
    record = session.get(Record, image.record_id)
    filename = image.filename
    session.delete(image)
    session.flush()
    session.expire(record, ["images"])
    for position, rest in enumerate(record.images):  # порядок без дыр
        rest.position = position
    session.commit()
    delete_image_files([filename])
