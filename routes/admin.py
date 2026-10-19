from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

import data.db as db
from data.schemas import RecordCreate
from core import templates, settings
from utils.logger import get_logger

router = APIRouter()

logger = get_logger(__name__)

TAGS = [
    ("Легкий уровень", "easy"),
    ("Средний уровень", "medium"),
    ("Тяжелый уровень", "hard"),
    ("Послушание", "obedience"),
    ("Контроль импульсов", "impulse_control"),
]


@router.get("/admin")
async def admin(
    request: Request,
):
    cards = []
    logger.info("Admin panel was requested. Is empty now, no db added.")
    return templates.TemplateResponse(
        request=request,
        name="pages/admin.html",
        context={
            "page_description": "Админка проекта. Здесь можно добавлять и удалять команды.",
            "cards": cards,
            "adminMode": settings.ADMIN_MODE,
            "tags": TAGS,
        },
    )


@router.post("/save_card")
async def save_card(
    request: Request,
    session=Depends(db.get_db),
    title: str = Form(...),
    description: str = Form(...),
    text: str = Form(...),
    record_type: str = Form(...),
    tags: list = Form([]),
):

    new_record = RecordCreate(
        title=title,
        description=description,
        text=text,
        record_type=record_type,
        tags=tags,
    )

    db.create_record(session=session, data=new_record.model_dump())
    return RedirectResponse(url=request.url_for("admin"), status_code=303)


@router.post("/delete_card")
async def delete_card(
    request: Request,
    card_id: int = Form(...),
):
    logger.info("Admin panel got a delete request. Is empty now, no db added.")
    return RedirectResponse(url=request.url_for("admin"), status_code=303)
