# Testing and learning form interactions and pydantic models

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from core import templates

from pydantic import BaseModel

from utils.logger import get_logger

router = APIRouter()

logger = get_logger(__name__)


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
        logger.warning("Api got post without all fields filled.")
        return RedirectResponse(url=request.url_for("get_api"), status_code=303)
    new_user = User(name=name, text=text, tags=tags)
    users.append(new_user)
    logger.info("Api got new user: %s", new_user)

    return RedirectResponse(url=request.url_for("get_api"), status_code=303)
