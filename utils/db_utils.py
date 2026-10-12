import sys
from pathlib import Path

# 1. Определяем корневую директорию проекта (на уровень выше папки utils)
ROOT_DIR = Path(__file__).resolve().parent.parent

# 2. Добавляем корень в sys.path, чтобы Python нашел модуль db
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import json

# 3. Теперь импорт отработает корректно
from db import init_db, Card, async_session_factory

# Путь к JSON файлу в той же директории, что и этот скрипт (в папке utils)
JSON_FILE_PATH = Path(__file__).parent / "default_data.json"


async def load_cards_from_json() -> None:
    """
    Инициализирует БД и загружает карточки из JSON файла.
    """
    await init_db()

    if not JSON_FILE_PATH.exists():
        print(
            f"❌ Файл {JSON_FILE_PATH.name} не найден в папке {JSON_FILE_PATH.parent.name}."
        )
        return

    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("❌ JSON должен содержать список объектов (карточек).")
        return

    async with async_session_factory() as session:
        cards_to_add = []

        for item in data:
            title = str(item.get("title", "")).strip()
            description = str(item.get("description", "")).strip()
            tags = item.get("tags", [])

            if not isinstance(tags, list):
                tags = []

            if title and description:
                cards_to_add.append(
                    Card(title=title, description=description, tags=tags)
                )

        if cards_to_add:
            session.add_all(cards_to_add)
            await session.commit()
            print(f"✅ Успешно загружено {len(cards_to_add)} карточек в БД.")
        else:
            print("⚠️ Нет валидных данных для загрузки.")


if __name__ == "__main__":
    asyncio.run(load_cards_from_json())
