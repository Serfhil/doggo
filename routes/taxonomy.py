from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import data.db as db
from core import templates
from data import taxonomy
from data.models import Category, Tag

router = APIRouter(prefix="/admin/taxonomy")


def _page(request: Request, session: Session, error: str | None = None, notice=None):
    return templates.TemplateResponse(
        request=request,
        status_code=422 if error else 200,
        name="admin/taxonomy.html",
        context={
            "tags": taxonomy.tags_with_counts(session),
            "categories": taxonomy.categories_with_counts(session),
            "error": error,
            "notice": notice,
        },
    )


def _run(request: Request, session: Session, action, message: str):
    """Выполняет действие; при ошибке показывает страницу с сообщением."""
    try:
        action()
    except taxonomy.TaxonomyError as exc:
        session.rollback()
        return _page(request, session, error=str(exc))
    return RedirectResponse(f"/admin/taxonomy?msg={message}", status_code=303)


@router.get("")
def taxonomy_page(request: Request, session: Session = Depends(db.get_db)):
    notice = {
        "ok": "Готово",
    }.get(request.query_params.get("msg", ""))
    return _page(request, session, notice=notice)


@router.post("/tags/add")
def add_tag(
    request: Request, session: Session = Depends(db.get_db), name: str = Form("")
):
    return _run(request, session, lambda: taxonomy.add_tag(session, name), "ok")


@router.post("/tags/{tag_id}/rename")
def rename_tag(
    request: Request,
    tag_id: int,
    session: Session = Depends(db.get_db),
    name: str = Form(""),
):
    return _run(
        request, session, lambda: taxonomy.rename(session, Tag, tag_id, name), "ok"
    )


@router.post("/tags/{tag_id}/delete")
def delete_tag(
    request: Request, tag_id: int, session: Session = Depends(db.get_db)
):
    return _run(request, session, lambda: taxonomy.delete_tag(session, tag_id), "ok")


@router.post("/tags/{tag_id}/merge")
def merge_tag(
    request: Request,
    tag_id: int,
    session: Session = Depends(db.get_db),
    target_id: int = Form(0),
):
    return _run(
        request, session, lambda: taxonomy.merge_tags(session, tag_id, target_id), "ok"
    )


@router.post("/categories/add")
def add_category(
    request: Request, session: Session = Depends(db.get_db), name: str = Form("")
):
    return _run(request, session, lambda: taxonomy.add_category(session, name), "ok")


@router.post("/categories/{category_id}/rename")
def rename_category(
    request: Request,
    category_id: int,
    session: Session = Depends(db.get_db),
    name: str = Form(""),
):
    return _run(
        request,
        session,
        lambda: taxonomy.rename(session, Category, category_id, name),
        "ok",
    )


@router.post("/categories/{category_id}/delete")
def delete_category(
    request: Request, category_id: int, session: Session = Depends(db.get_db)
):
    return _run(
        request, session, lambda: taxonomy.delete_category(session, category_id), "ok"
    )


@router.post("/categories/{category_id}/move")
def move_category(
    request: Request,
    category_id: int,
    session: Session = Depends(db.get_db),
    target_id: int = Form(0),
):
    return _run(
        request,
        session,
        lambda: taxonomy.move_category_records(session, category_id, target_id),
        "ok",
    )
