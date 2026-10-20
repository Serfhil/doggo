# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core import BASE_DIR
from utils.logger import get_logger, setup_logging
from data.db import init_db

# Импортируем наши роутеры
from routes import index, admin, record, api

setup_logging()
logger = get_logger(__name__)


app = FastAPI()

# Монтируем статику
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), check_dir=False),
    name="static",
)

# Подключаем роутеры из папки routes
app.include_router(index.router)
app.include_router(admin.router)
app.include_router(record.router)
app.include_router(api.router)

# Инициализируем бд
init_db()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
