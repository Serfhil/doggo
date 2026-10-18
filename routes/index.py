# routes/pages.py
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import data.db as db
from core import templates, settings

router = APIRouter()


@router.get("/")
async def read_root(request: Request, session=Depends(db.get_db)):
    db.init_db()
    cards = db.get_records_paginated(session=session, limit=100)
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
