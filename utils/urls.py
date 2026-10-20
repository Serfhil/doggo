"""Ссылки на список с фильтрами. Берём только известные параметры (без открытых редиректов)."""
from urllib.parse import urlencode

LIST_PARAMS = ("category", "tag", "q", "page")


def list_query(params: dict) -> str:
    """Строка запроса только из разрешённых непустых параметров."""
    clean = {k: params[k] for k in LIST_PARAMS if params.get(k) not in (None, "", 0)}
    return urlencode(clean)


def with_query(path: str, params: dict) -> str:
    query = list_query(params)
    return f"{path}?{query}" if query else path
