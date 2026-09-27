from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.document import DocumentRead
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Enterprise Document",
    description="Upload original enterprise document (PDF, DOCX, TXT) and store file with database record.",
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    access_level: Optional[str] = Form("internal"),
    db: Session = Depends(get_db),
):
    doc_record = await document_service.upload_document(
        db=db,
        file=file,
        title=title,
        document_type=document_type,
        department=department,
        access_level=access_level,
    )
    return doc_record
