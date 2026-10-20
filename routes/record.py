from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
import data.db as db
from data.schemas import RecordRead

from utils.logger import get_logger
from core import templates


router = APIRouter()

logger = get_logger(__name__)


@router.get("/record/{record_id}")
async def record(
    request: Request,
    record_id: int,
    session=Depends(db.get_db),
):
    record = db.get_record_by_id(session=session, record_id=record_id)
    if record:
        # ORM-объект -> pydantic-схема, дальше можно model_dump()
        record_dict = RecordRead.model_validate(record).model_dump()
    else:
        logger.warning("Tried to get record by id. None found")
        return RedirectResponse(url=request.url_for("read_root"), status_code=404)

    return templates.TemplateResponse(
        request=request, name="pages/record.html", context=record_dict
    )
