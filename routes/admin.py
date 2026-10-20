from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import data.db as db
from core import settings, templates
from data import records, taxonomy
from data.models import Category
from data.schemas import RecordForm
from routes.record import render_record
from utils.logger import get_logger
from utils.text import sanitize_html

router = APIRouter(prefix="/admin")
logger = get_logger(__name__)

ADMIN_PAGE_SIZE = 30


def _int(value: str | None) -> int | None:
    return int(value) if value and value.strip().isdigit() else None


@router.get("")
def admin_list(request: Request, session: Session = Depends(db.get_db)):
    params = request.query_params
    page = _int(params.get("page")) or 1
    filters = {
        "q": (params.get("q") or "").strip()[:100],
        "category_id": _int(params.get("category")),
        "status": params.get("status") or "",
    }
    items, total = records.list_records(
        session,
        page=page,
        page_size=ADMIN_PAGE_SIZE,
        published_only=False,
        **filters,
    )
    pages = max(-(-total // ADMIN_PAGE_SIZE), 1)
    return templates.TemplateResponse(
        request=request,
        name="admin/list.html",
        context={
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "filters": filters,
            "categories": taxonomy.all_categories(session),
            "notice": {"deleted": "Запись удалена"}.get(params.get("msg", "")),
        },
    )


def _form_page(
    request: Request,
    session: Session,
    *,
    record=None,
    values: dict | None = None,
    selected_tags: set[int] | None = None,
    errors: dict | None = None,
    new_tags: str = "",
    notice: str | None = None,
):
    if values is None:
        if record:
            values = {
                "title": record.title,
                "category_id": record.category_id,
                "description": record.description,
                "text": record.text,
                "is_published": record.is_published,
            }
        else:
            values = {"is_published": True}
    if selected_tags is None:
        selected_tags = {t.id for t in record.tags} if record else set()
    return templates.TemplateResponse(
        request=request,
        status_code=422 if errors else 200,
        name="admin/form.html",
        context={
            "record": record,
            "values": values,
            "errors": errors or {},
            "categories": taxonomy.all_categories(session),
            "tags": taxonomy.all_tags(session),
            "selected_tags": selected_tags,
            "new_tags": new_tags,
            "notice": notice,
            "max_images": settings.MAX_IMAGES_PER_RECORD,
        },
    )


@router.get("/new")
def new_form(request: Request, session: Session = Depends(db.get_db)):
    return _form_page(request, session)


@router.get("/edit/{record_id}")
def edit_form(
    request: Request, record_id: int, session: Session = Depends(db.get_db)
):
    record = records.get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404)
    notice = "Запись сохранена" if request.query_params.get("saved") else None
    return _form_page(request, session, record=record, notice=notice)


def _handle_save(
    request: Request,
    session: Session,
    record,
    *,
    title: str,
    category_id: str,
    description: str,
    text: str,
    tags: list[int],
    new_tags: str,
    is_published: str,
):
    form = RecordForm(
        title=title,
        category_id=_int(category_id),
        description=description,
        text=sanitize_html(text),
        is_published=is_published == "on",
    )
    errors = form.errors()
    if form.category_id is not None and not session.get(Category, form.category_id):
        errors["category_id"] = "Такой категории нет"
    try:
        if not errors:
            saved = records.save_record(session, record, form, tags, new_tags)
            return RedirectResponse(f"/admin/edit/{saved.id}?saved=1", status_code=303)
    except taxonomy.TaxonomyError as exc:
        session.rollback()
        errors["new_tags"] = str(exc)
    return _form_page(
        request,
        session,
        record=record,
        values=form.model_dump(),
        selected_tags=set(tags),
        errors=errors,
        new_tags=new_tags,
    )


@router.post("/new")
def create(
    request: Request,
    session: Session = Depends(db.get_db),
    title: str = Form(""),
    category_id: str = Form(""),
    description: str = Form(""),
    text: str = Form(""),
    tags: list[int] = Form([]),
    new_tags: str = Form(""),
    is_published: str = Form(""),
):
    return _handle_save(
        request, session, None, title=title, category_id=category_id,
        description=description, text=text, tags=tags, new_tags=new_tags,
        is_published=is_published,
    )


@router.post("/edit/{record_id}")
def update(
    request: Request,
    record_id: int,
    session: Session = Depends(db.get_db),
    title: str = Form(""),
    category_id: str = Form(""),
    description: str = Form(""),
    text: str = Form(""),
    tags: list[int] = Form([]),
    new_tags: str = Form(""),
    is_published: str = Form(""),
):
    record = records.get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404)
    return _handle_save(
        request, session, record, title=title, category_id=category_id,
        description=description, text=text, tags=tags, new_tags=new_tags,
        is_published=is_published,
    )


@router.post("/delete/{record_id}")
def delete(record_id: int, session: Session = Depends(db.get_db)):
    if not records.delete_record(session, record_id):
        raise HTTPException(status_code=404)
    return RedirectResponse("/admin?msg=deleted", status_code=303)


@router.get("/preview/{record_id}")
def preview(
    request: Request, record_id: int, session: Session = Depends(db.get_db)
):
    record = records.get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404)
    return render_record(request, record, preview=True)
