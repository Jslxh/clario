import uuid
import logging
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.services.file_storage import file_storage_service
from app.services.parsers.factory import ParserFactory
from app.schemas.parser import ParsedDocument

logger = logging.getLogger(__name__)

# Known MIME types mapping
MIME_MAPPINGS = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/x-zip-compressed",
        "application/zip",
        "application/octet-stream",
    },
    "txt": {"text/plain", "text/csv", "application/octet-stream"},
}


class DocumentService:
    """Service handling document upload validation, file persistence, database registration, and parsing."""

    def __init__(self, storage=None):
        self.storage = storage or file_storage_service

    def validate_file_type_and_extension(self, filename: str) -> str:
        """Extract and validate extension against supported types (pdf, docx, txt)."""
        sanitized = self.storage.sanitize_filename(filename)
        if "." not in sanitized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File has no extension. Supported formats: PDF, DOCX, TXT.",
            )
        
        ext = sanitized.rsplit(".", 1)[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}'. Supported formats: PDF, DOCX, TXT.",
            )
        return ext

    def validate_magic_bytes(self, content: bytes, ext: str) -> None:
        """Validate file header magic bytes to prevent mislabeled executable binaries."""
        if ext == "pdf":
            if not content.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PDF file content header.",
                )
        elif ext == "docx":
            # DOCX files are OpenXML ZIP archives starting with PK\x03\x04
            if not content.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DOCX file content header.",
                )

    async def upload_document(
        self,
        db: Session,
        file: UploadFile,
        title: Optional[str] = None,
        document_type: Optional[str] = None,
        department: Optional[str] = None,
        access_level: Optional[str] = "internal",
    ) -> Document:
        """Handle multipart file upload, storage, and database persistence."""
        filename = file.filename or "uploaded_file"
        
        # 1. Validate extension
        ext = self.validate_file_type_and_extension(filename)
        sanitized_filename = self.storage.sanitize_filename(filename)

        # 2. Read file contents
        content = await file.read()
        file_size = len(content)

        # 3. Validate non-empty
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        # 4. Validate file size limits
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed limit of {max_mb}MB.",
            )

        # 5. Validate file magic bytes
        self.validate_magic_bytes(content, ext)

        # 6. Generate UUID & storage path
        doc_uuid = uuid.uuid4()
        doc_id_str = str(doc_uuid)

        stored_file_path = ""
        try:
            # 7. Persist original binary file to storage
            stored_file_path = self.storage.save_file(
                document_id=doc_id_str,
                file_bytes=content,
                extension=ext,
            )

            # 8. Create DB record
            doc_record = Document(
                id=doc_uuid,
                filename=sanitized_filename,
                title=title.strip() if title and title.strip() else sanitized_filename,
                document_type=document_type.lower() if document_type else ext,
                department=department.strip() if department else None,
                access_level=access_level.strip() if access_level else "internal",
                file_path=stored_file_path,
                file_size=file_size,
                status=DocumentStatus.UPLOADED,
                uploaded_by=None,
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)

            logger.info(f"Successfully uploaded and registered document {doc_id_str}")
            return doc_record

        except Exception as err:
            db.rollback()
            if doc_id_str:
                self.storage.delete_file_directory(doc_id_str)
            if isinstance(err, HTTPException):
                raise err
            logger.error(f"Failed to process document upload: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database or file storage error occurred while processing document.",
            ) from err

    def parse_document(self, db: Session, document_id: str) -> ParsedDocument:
        """Retrieve document record from DB and parse file content into normalized representation."""
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document UUID: {document_id}",
            ) from err

        doc_record = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )

        if not self.storage.file_exists(doc_record.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original document file missing at '{doc_record.file_path}'.",
            )

        return ParserFactory.parse_document(
            file_path=doc_record.file_path,
            document_id=str(doc_record.id),
            filename=doc_record.filename,
            document_type=doc_record.document_type,
        )


document_service = DocumentService()
