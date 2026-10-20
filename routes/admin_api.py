"""JSON-эндпоинты для интерактивных блоков админки (контракт: ТЗ, 2.8)."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

import data.db as db
from core import settings
from data import images as image_service
from data import records
from data.models import Image
from utils.images import ImageError

router = APIRouter(prefix="/admin/api")


class AltBody(BaseModel):
    alt: str


class OrderBody(BaseModel):
    ids: list[int]


def _record(session: Session, record_id: int):
    record = records.get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return record


def _image(session: Session, image_id: int) -> Image:
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Картинка не найдена")
    return image


@router.post("/records/{record_id}/images", status_code=201)
def upload_image(
    record_id: int, file: UploadFile, session: Session = Depends(db.get_db)
):
    record = _record(session, record_id)
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = file.file.read(limit + 1)  # читаем на байт больше лимита, чтобы заметить превышение
    try:
        image = image_service.add_image(session, record, data)
    except ImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return image_service.image_dict(image)


@router.patch("/images/{image_id}")
def update_alt(image_id: int, body: AltBody, session: Session = Depends(db.get_db)):
    image = image_service.set_alt(session, _image(session, image_id), body.alt)
    return image_service.image_dict(image)


@router.put("/records/{record_id}/images/order")
def reorder_images(
    record_id: int, body: OrderBody, session: Session = Depends(db.get_db)
):
    record = _record(session, record_id)
    try:
        image_service.reorder(session, record, body.ids)
    except ImageError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return [image_service.image_dict(i) for i in record.images]


@router.delete("/images/{image_id}", status_code=204)
def remove_image(image_id: int, session: Session = Depends(db.get_db)):
    image_service.delete_image(session, _image(session, image_id))
