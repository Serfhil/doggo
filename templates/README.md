# templates

HTML-шаблоны Jinja2. Подключаются через объект `templates` из [core.py](../core.py).

## Файлы

| Файл | Кто использует | Что это |
|------|----------------|---------|
| `base.html` | все публичные страницы | Общий каркас: `head`, шрифты, шапка с меню, блоки `title`, `meta`, `head`, `content`, `scripts` |
| `pages/main.html` | `GET /` | Главная: поиск, фильтр по категориям, карточки, пагинация |
| `pages/record.html` | `GET /record/{id}`, предпросмотр в админке | Страница записи: картинки, текст, теги, ссылка «назад» |
| `pages/error.html` | обработчики ошибок в `main.py` | Страница 404, 405 и 500 |
| `admin/base.html` | все страницы админки | Наследует `base.html`, подключает `admin.css`, `common.js` и меню админки |
| `admin/list.html` | `GET /admin` | Список записей с фильтрами и удалением |
| `admin/form.html` | `/admin/new`, `/admin/edit/{id}` | Форма записи: Quill, теги, менеджер картинок (Vue) |
| `admin/taxonomy.html` | `/admin/taxonomy` | Теги и категории |
| `partials/card.html` | include в `main.html` | Карточка записи, ждёт `card` и `card_url` |
| `partials/top_panel.html` | `base.html` | Меню публичного сайта |
| `partials/admin_nav.html` | `admin/base.html` | Меню админки, активный пункт определяется по пути запроса |

## Как страницы получают данные

Роут передаёт `context` в `TemplateResponse`, а шаблон обращается к его ключам.

- `main.html`: `cards`, `categories`, `active_tag`, `filters`, `page`, `pages`, `url_with`, `record_url`, `meta_description`.
- `record.html`: `record`, `back_url`, `preview`.
- `admin/list.html`: `items`, `total`, `page`, `pages`, `filters`, `categories`, `notice`.
- `admin/form.html`: `record`, `values`, `errors`, `categories`, `tags`, `selected_tags`, `new_tags`, `notice`, `images`, `max_images`, `max_upload_mb`.
- `admin/taxonomy.html`: `tags`, `categories` (пары «объект, число записей»), `error`, `notice`.

Общее для всех шаблонов (задано в `core.py`): `settings`, фильтры `date` и `datetime` (время сайта, а не UTC),
функция `summary(record)` (краткое описание или начало текста).

## Правила

- Ссылки на статику строятся через `url_for('static', path='...')`, ссылки на картинки записи — `/uploads/<файл>`.
- Автоэкранирование Jinja включено. `|safe` стоит один раз, в `record.html`, для `record.text`:
  этот HTML уже очищен на сервере (`utils/text.py`). Больше нигде `|safe` не нужен.
- Формы админки отправляют `POST`; имена полей (`name="..."`) должны совпадать с параметрами `Form(...)`
  в [routes/admin.py](../routes/admin.py).
- Подтверждение удаления делается атрибутом `data-confirm="..."` у формы, а не inline-JS (обрабатывает `static/admin/common.js`).
- Форма записи (`data-guard`) предупреждает об уходе со страницы с несохранёнными изменениями.
- Шрифты пока грузятся с Google Fonts (см. комментарий в `base.html`).
