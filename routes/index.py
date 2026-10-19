from fastapi import APIRouter, Depends, Request
import data.db as db
from data.schemas import RecordRead
from core import templates, settings

router = APIRouter()


@router.get("/")
async def read_root(request: Request, session=Depends(db.get_db)):
    # Превращаем ORM-объекты в pydantic-схемы: шаблон получает чистые данные
    cards = [
        RecordRead.model_validate(record)
        for record in db.get_records_paginated(session=session, limit=100)
    ]
    return templates.TemplateResponse(
        request=request,
        name="pages/main.html",
        context={
            "title": "Тари тренирует собачку",
            "heading": "Добро пожаловать!",
            "cards": cards,
            "adminMode": settings.ADMIN_MODE,
        },
    )
