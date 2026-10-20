# Тренируем собачку

Справочник по тренировке собак: записи с категориями, тегами и картинками.
FastAPI + SQLite + Jinja. Редактор текста Quill и менеджер картинок (Vue) лежат локально в `static/vendor/`.
Подробное ТЗ и план: [расширенное техническое задание.md](расширенное%20техническое%20задание.md).

## Запуск

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # поправь под себя
python main.py              # http://127.0.0.1:8000, админка: /admin
```

База (`data/app.db`) и папка `uploads/` создаются при первом запуске.

## Тесты

```bash
python -m pytest
```

## Команды в терминале

```bash
python -m cli export [-o файл.json]       # выгрузка записей в JSON
python -m cli import файл.json            # добавить и обновить записи
python -m cli import файл.json --replace  # заменить всё (только отсюда, не через сайт)
python -m cli backup                      # копия базы в backups/
python -m cli check-files                 # картинки без записи и записи без файла
```

Схема БД без миграций: чтобы изменить схему, сделай `export`, удали `data/app.db`,
запусти приложение и сделай `import`.
