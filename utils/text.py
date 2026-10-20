import html
import re

import nh3

# Разрешённый HTML основного текста (ТЗ, 2.2). img не разрешён: картинки лежат отдельно
ALLOWED_TAGS = {
    "p", "br", "h2", "h3", "strong", "em", "u", "s",
    "ul", "ol", "li", "blockquote", "a",
}
ALLOWED_ATTRIBUTES = {"a": {"href"}, "li": {"data-list"}}
ALLOWED_SCHEMES = {"http", "https", "mailto"}

_TAG_RE = re.compile(r"<[^>]+>")


def normalize_key(value: str) -> str:
    """Ключ для сравнения без учёта регистра: работает и для кириллицы (в SQLite нет)."""
    return " ".join(value.split()).casefold().replace("ё", "е")


def clean_name(value: str) -> str:
    """Название тега или категории: без лишних пробелов."""
    return " ".join(value.split())


def sanitize_html(value: str) -> str:
    cleaned = nh3.clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
    ).strip()
    # Пустой Quill выдаёт <p><br></p>: считаем такой текст пустым
    return "" if not html_to_plain(cleaned) else cleaned


def html_to_plain(value: str) -> str:
    """Текст без разметки (для проверки на пустоту и краткого фрагмента)."""
    text = _TAG_RE.sub(" ", value or "")
    return " ".join(html.unescape(text).split())


def excerpt(value: str, limit: int = 150) -> str:
    plain = html_to_plain(value)
    if len(plain) <= limit:
        return plain
    return plain[:limit].rsplit(" ", 1)[0].rstrip(",.;:- ") + "…"


def build_search_text(title: str, description: str) -> str:
    return normalize_key(f"{title} {description}")
