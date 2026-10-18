# Testing and learning form interactions and pydantic models

from typing import Annotated
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import templates, settings

from pydantic import BaseModel

from rich import print

router = APIRouter()


users = []


class User(BaseModel):
    name: str
    text: str
    tags: list


@router.get("/api")
async def get_api(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="api_base.html",
        context={
            "title": "Добавляем пользователей",
            "users": users,
        },
    )


@router.post("/api/submit", name="submit")
async def post_api(
    request: Request,
    name: str = Form(...),
    text: str = Form(...),
    tags: list = Form(...),
):
    if not name or not text or not tags:
        print("Api got post without all fields filled.")
        return RedirectResponse(url=request.url_for("get_api"), status_code=303)
    new_user = User(name=name, text=text, tags=tags)
    users.append(new_user)
    print(new_user)

    return RedirectResponse(url=request.url_for("get_api"), status_code=303)
