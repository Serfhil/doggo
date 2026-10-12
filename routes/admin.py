# routes/admin.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import db
from core import templates, settings, _collect_unique_tags, _normalize_tags

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(db.get_db)]


@router.get("/admin")
async def admin(request: Request, session: DbSession):
    result = await session.execute(select(db.Card).order_by(db.Card.id.desc()))
    cards = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="pages/admin.html",
        context={
            "page_description": "Админка проекта. Здесь можно добавлять и удалять команды.",
            "cards": cards,
            "tags": _collect_unique_tags(cards),
            "adminMode": settings.ADMIN_MODE,
        },
    )


@router.post("/save_card")
async def save_card(
    request: Request,
    session: DbSession,
    title: str = Form(...),
    description: str = Form(...),
    tags: List[str] = Form(default=[]),
):
    clean_title = title.strip()
    clean_description = description.strip()
    clean_tags = _normalize_tags(tags)

    if not clean_title:
        raise HTTPException(status_code=422, detail="Заголовок не может быть пустым")
    if not clean_description:
        raise HTTPException(status_code=422, detail="Описание не может быть пустым")
    if len(clean_title) > db.TITLE_MAX_LENGTH:
        raise HTTPException(
            status_code=422, detail=f"Заголовок длиннее {db.TITLE_MAX_LENGTH} символов"
        )
    if len(clean_description) > db.DESCRIPTION_MAX_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Описание длиннее {db.DESCRIPTION_MAX_LENGTH} символов",
        )
    if any(len(tag) > db.TAG_MAX_LENGTH for tag in clean_tags):
        raise HTTPException(
            status_code=422, detail=f"Тег длиннее {db.TAG_MAX_LENGTH} символов"
        )

    card = db.Card(title=clean_title, description=clean_description, tags=clean_tags)
    session.add(card)
    await session.commit()

    return RedirectResponse(url=request.url_for("admin"), status_code=303)


@router.post("/delete_card")
async def delete_card(
    request: Request,
    session: DbSession,
    card_id: int = Form(...),
):
    result = await session.execute(select(db.Card).where(db.Card.id == card_id))
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    await session.delete(card)
    await session.commit()

    return RedirectResponse(url=request.url_for("admin"), status_code=303)
