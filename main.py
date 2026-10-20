# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core import BASE_DIR, settings, templates
from data.db import init_db
from routes import admin, admin_api, index, record, taxonomy
from utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # БД создаётся при старте приложения, а не при импорте модуля (иначе тесты трогают боевую БД)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), check_dir=False),
    name="static",
)
# Загруженные картинки. На VPS их отдаёт nginx
app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path), check_dir=False),
    name="uploads",
)

app.include_router(index.router)
app.include_router(record.router)
app.include_router(admin.router)
app.include_router(taxonomy.router)
app.include_router(admin_api.router)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def html_errors(request: Request, exc: StarletteHTTPException):
    # JSON-эндпоинты и не-HTML ответы оставляем как есть
    if request.url.path.startswith("/admin/api") or exc.status_code not in (404, 405):
        return await http_exception_handler(request, exc)
    heading = "Страница не найдена" if exc.status_code == 404 else "Так нельзя"
    return templates.TemplateResponse(
        request=request,
        status_code=exc.status_code,
        name="pages/error.html",
        context={
            "heading": heading,
            "message": "Такой страницы нет. Возможно, запись удалена или ещё не опубликована.",
        },
    )


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return templates.TemplateResponse(
        request=request,
        status_code=500,
        name="pages/error.html",
        context={
            "heading": "Что-то пошло не так",
            "message": "Ошибка на сервере. Попробуйте обновить страницу чуть позже.",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
