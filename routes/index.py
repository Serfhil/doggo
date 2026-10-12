# routes/pages.py
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import db
from core import templates, settings

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(db.get_db)]


@router.get("/")
async def read_root(request: Request, session: DbSession):
    result = await session.execute(select(db.Card).order_by(db.Card.id.desc()))
    cards = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="pages/main.html",
        context={
            "title": "Моя записная книжка",
            "heading": "Добро пожаловать!",
            "cards": cards,
            "adminMode": settings.ADMIN_MODE,
        },
    )
