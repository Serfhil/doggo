import math

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

import data.db as db
from core import settings, templates
from data import records, taxonomy
from data.models import Tag
from utils.urls import list_query, with_query

router = APIRouter()


def _int(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


@router.get("/")
def read_root(request: Request, session: Session = Depends(db.get_db)):
    params = request.query_params
    filters = {
        "category": _int(params.get("category")),
        "tag": _int(params.get("tag")),
        "q": (params.get("q") or "").strip()[:100],
    }
    page = _int(params.get("page")) or 1

    cards, total = records.list_records(
        session,
        page=page,
        page_size=settings.PAGE_SIZE,
        category_id=filters["category"],
        tag_id=filters["tag"],
        q=filters["q"],
    )
    pages = max(math.ceil(total / settings.PAGE_SIZE), 1)

    def url_with(**changes):
        """Текущие фильтры + изменения (None убирает параметр)."""
        merged = {**filters, "page": page if page > 1 else None, **changes}
        return with_query("/", merged)

    def record_url(card):
        # Фильтры уходят в ссылку, чтобы «назад» вёл на тот же список
        query = list_query({**filters, "page": page if page > 1 else None})
        return f"/record/{card.id}" + (f"?{query}" if query else "")

    return templates.TemplateResponse(
        request=request,
        name="pages/main.html",
        context={
            "meta_description": "Справочник по тренировке собак: команды, упражнения, игры и игрушки.",
            "cards": cards,
            "categories": taxonomy.all_categories(session),
            "active_tag": session.get(Tag, filters["tag"]) if filters["tag"] else None,
            "filters": filters,
            "page": page,
            "pages": pages,
            "url_with": url_with,
            "record_url": record_url,
        },
    )
