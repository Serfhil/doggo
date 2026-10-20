"""Команды для терминала: python -m cli <команда>.

  export [-o файл]            выгрузить записи в JSON
  import файл [--replace]     загрузить записи из JSON (--replace стирает всё, только отсюда)
  backup                      копия файла БД в backups/
  check-files                 найти картинки без записи в БД и записи без файла
"""
import argparse
import json
import sys
from datetime import datetime

from core import settings
from data import exchange
from data.db import SessionLocal, init_db
from data.models import Image
from utils.backup import backup_database


def cmd_export(args) -> int:
    with SessionLocal() as session:
        payload = exchange.export_data(session)
    # ensure_ascii=False: русский текст остаётся читаемым
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    target = args.output or f"export-{datetime.now():%Y%m%d-%H%M%S}.json"
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"Выгружено записей: {len(payload['records'])} -> {target}")
    return 0


def cmd_import(args) -> int:
    try:
        with open(args.file, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Не удалось прочитать файл: {exc}", file=sys.stderr)
        return 1
    if args.replace and not args.yes:
        answer = input(
            "Режим --replace удалит ВСЕ записи, теги и категории (картинки тоже). "
            "Копия базы будет сделана. Продолжить? [y/N] "
        )
        if answer.strip().lower() != "y":
            print("Отменено")
            return 1
    backup = backup_database(prefix="before-import")
    if backup:
        print(f"Копия базы: {backup}")
    try:
        with SessionLocal() as session:
            report = exchange.import_data(session, payload, replace=args.replace)
    except exchange.ImportFailed as exc:
        print("Файл не принят, база не изменена:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    for warning in report.warnings:
        print(f"Предупреждение: {warning}")
    print("Готово:", report.summary())
    return 0


def cmd_backup(_args) -> int:
    path = backup_database()
    print(f"Копия: {path}" if path else "Файла базы ещё нет")
    return 0


def cmd_check_files(_args) -> int:
    folder = settings.upload_path
    on_disk = {p.name for p in folder.glob("*.webp")} if folder.exists() else set()
    with SessionLocal() as session:
        in_db = {i.filename for i in session.query(Image)}
    expected = in_db | {f.replace(".webp", "_thumb.webp") for f in in_db}
    orphans, missing = sorted(on_disk - expected), sorted(expected - on_disk)
    for name in orphans:
        print(f"Файл без записи в БД: {name}")
    for name in missing:
        print(f"Запись без файла: {name}")
    print(f"Лишних файлов: {len(orphans)}, потерянных: {len(missing)}")
    return 1 if missing else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("export")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("import")
    p.add_argument("file")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--yes", action="store_true", help="не спрашивать подтверждение")
    p.set_defaults(func=cmd_import)
    sub.add_parser("backup").set_defaults(func=cmd_backup)
    sub.add_parser("check-files").set_defaults(func=cmd_check_files)
    args = parser.parse_args(argv)
    init_db()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
