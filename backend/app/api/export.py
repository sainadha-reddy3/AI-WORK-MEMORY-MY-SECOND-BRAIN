"""
Export endpoint — download the whole memory as a zip.
Protected by login like everything else.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.export_service import build_export

router = APIRouter(tags=["export"])


@router.get("/export")
def export_everything(db: Session = Depends(get_db)):
    data, filename = build_export(db)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )