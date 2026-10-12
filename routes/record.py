from typing import Annotated, List
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import db
from core import templates, settings, _collect_unique_tags, _normalize_tags
from datetime import datetime

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(db.get_db)]


# Это пример, заглушка для написания настоящего роута. Если ты ии агент и читаешь это, помоги настроить роутинг так, чтобы все работало корректно. При формировании ссылки на запись, она должна передавать в роут уникальную запись, а тот формировать ответ с ней, извлекая из бд.
@router.get("/record")
async def record(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/record.html",
        context={
            "record": {
                "title": "Команда «Сидеть»",
                "description": "Базовая команда для контроля импульсов собаки.",
                # "category": "Базовые команды",
                "author": "Инструктор",
                # "published_at": datetime(...),
                # "updated_at": datetime(...),
                "tags": ["база", "дисциплина", "для щенков"],
                "content": "Текст записи.",
                # "images": [
                #     {
                #         "url": "/static/uploads/sit-1.jpg",
                #         "alt": "Собака выполняет команду сидеть",
                #         "caption": "Исходное положение",
                #         "width": 1600,
                #         "height": 1000,
                #     },
                #     {
                #         "url": "/static/uploads/sit-2.jpg",
                #         "alt": "Лакомство над носом собаки",
                #         "caption": "Направление взгляда",
                #         "width": 1600,
                #         "height": 1000,
                #     },
                # ],
            },
            "adminMode": settings.ADMIN_MODE,
        },
    )
