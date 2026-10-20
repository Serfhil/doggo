from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import data.db as db
from core import templates
from data import records
from utils.urls import with_query

router = APIRouter()


def render_record(request: Request, record, preview: bool = False):
    # «Назад» строим из белого списка параметров, а не из Referer
    back_url = with_query("/", dict(request.query_params))
    return templates.TemplateResponse(
        request=request,
        name="pages/record.html",
        context={"record": record, "back_url": back_url, "preview": preview},
    )


@router.get("/record/{record_id}")
def record_page(
    request: Request, record_id: int, session: Session = Depends(db.get_db)
):
    record = records.get_record(session, record_id)
    # Черновики читателям не показываются
    if not record or not record.is_published:
        raise HTTPException(status_code=404)
    return render_record(request, record)
