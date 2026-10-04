import uuid
import logging
from typing import Optional, List, Tuple, Any
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
        uploaded_by: Optional[uuid.UUID] = None,
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
                uploaded_by=uploaded_by,
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)

            try:
                from app.services.audit_service import audit_service
                audit_service.log_event(
                    db=db,
                    action="upload",
                    resource_type="document",
                    user_id=uploaded_by,
                    resource_id=doc_id_str,
                    details={
                        "filename": sanitized_filename,
                        "file_size": file_size,
                        "department": department,
                        "access_level": access_level,
                    },
                )
            except Exception as audit_err:
                logger.warning(f"Failed to record upload audit log: {audit_err}")

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

        local_path = self.storage.get_local_filepath(doc_record.file_path)
        return ParserFactory.parse_document(
            file_path=local_path,
            document_id=str(doc_record.id),
            filename=doc_record.filename,
            document_type=doc_record.document_type,
        )

    def process_document_background(self, document_id: str) -> None:
        """Background task handler for processing a document asynchronously via FastAPI BackgroundTasks."""
        from app.core.database import SessionLocal
        from app.services.chunking.service import chunking_service
        from app.services.indexing_service import indexing_service
        from app.services.retrieval.bm25_index import bm25_index
        from app.services.audit_service import audit_service

        logger.info(f"Starting background processing for document: {document_id}")
        with SessionLocal() as db:
            try:
                doc_uuid = uuid.UUID(document_id)
                doc_record = db.query(Document).filter(Document.id == doc_uuid).first()
                if not doc_record:
                    logger.error(f"Background task: Document {document_id} not found in database.")
                    return

                # Ensure status is PROCESSING
                doc_record.status = DocumentStatus.PROCESSING
                db.commit()

                # Verify file existence via storage abstraction
                if not self.storage.file_exists(doc_record.file_path):
                    logger.error(f"Background task: Original document file missing at '{doc_record.file_path}'")
                    doc_record.status = DocumentStatus.FAILED
                    db.commit()
                    return

                # Parse document file using local path from storage
                local_path = self.storage.get_local_filepath(doc_record.file_path)
                parsed_doc = ParserFactory.parse_document(
                    file_path=local_path,
                    document_id=str(doc_record.id),
                    filename=doc_record.filename,
                    document_type=doc_record.document_type,
                )

                # Chunk document
                chunks = chunking_service.chunk_document(parsed_doc)

                # Persist chunks
                persisted_chunks = chunking_service.persist_chunks(db, document_id, chunks)

                # Index vectors in Qdrant
                indexing_service.index_document_chunks(db, document_id)

                # Transition to READY
                doc_record.status = DocumentStatus.READY
                db.commit()
                db.refresh(doc_record)

                # Synchronize in-memory BM25 index
                try:
                    bm25_index.index_document_chunks(
                        document_id=document_id,
                        chunks=persisted_chunks,
                        document=doc_record,
                    )
                except Exception as bm25_err:
                    logger.warning(f"Post-commit BM25 sync failed for {document_id}: {bm25_err}")
                    try:
                        bm25_index.invalidate()
                    except Exception:
                        pass

                # Record audit log
                try:
                    audit_service.log_event(
                        db=db,
                        action="process",
                        resource_type="document",
                        user_id=doc_record.uploaded_by,
                        resource_id=str(doc_record.id),
                        details={
                            "status": DocumentStatus.READY.value,
                            "chunk_count": len(persisted_chunks),
                        },
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to record process audit log: {audit_err}")

                logger.info(f"Background processing successfully finished for document {document_id}")

            except Exception as err:
                db.rollback()
                logger.error(f"Background processing failed for document {document_id}: {err}")
                try:
                    bm25_index.remove_document(document_id)
                except Exception:
                    pass

                try:
                    failed_doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
                    if failed_doc:
                        failed_doc.status = DocumentStatus.FAILED
                        db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update document status to FAILED in background task: {db_err}")

    def process_document(self, db: Session, document_id: str) -> Document:
        """Process document end-to-end: UPLOADED -> PROCESSING -> Parse -> Chunk -> Index -> READY / FAILED."""
        from app.services.chunking.service import chunking_service
        from app.services.indexing_service import indexing_service

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

        # 1. Transition status to PROCESSING
        doc_record.status = DocumentStatus.PROCESSING
        db.commit()
        db.refresh(doc_record)

        try:
            # 2. Check original file existence
            if not self.storage.file_exists(doc_record.file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Original document file missing at '{doc_record.file_path}'.",
                )

            # 3. Parse document file
            parsed_doc = ParserFactory.parse_document(
                file_path=doc_record.file_path,
                document_id=str(doc_record.id),
                filename=doc_record.filename,
                document_type=doc_record.document_type,
            )

            # 4. Chunk document
            chunks = chunking_service.chunk_document(parsed_doc)

            # 5. Persist chunks to PostgreSQL (idempotent replacement)
            persisted_chunks = chunking_service.persist_chunks(db, document_id, chunks)

            # 6. Generate embeddings & upsert vectors to Qdrant (idempotent point replacement)
            indexing_service.index_document_chunks(db, document_id)

            # 7. Transition status to READY and commit database transaction
            doc_record.status = DocumentStatus.READY
            db.commit()
            db.refresh(doc_record)

            # 8. Synchronize in-memory BM25 index post-commit (non-fatal auxiliary cache)
            try:
                from app.services.retrieval.bm25_index import bm25_index
                bm25_index.index_document_chunks(
                    document_id=document_id,
                    chunks=persisted_chunks,
                    document=doc_record,
                )
            except Exception as bm25_err:
                logger.warning(
                    f"Post-commit BM25 in-memory sync failed for document {document_id}: {bm25_err}. "
                    "Marking BM25 index uninitialized so it will rebuild from PostgreSQL on next query."
                )
                try:
                    from app.services.retrieval.bm25_index import bm25_index
                    bm25_index.invalidate()
                except Exception:
                    pass

            try:
                from app.services.audit_service import audit_service
                audit_service.log_event(
                    db=db,
                    action="process",
                    resource_type="document",
                    user_id=doc_record.uploaded_by,
                    resource_id=str(doc_record.id),
                    details={
                        "status": DocumentStatus.READY.value,
                        "chunk_count": len(persisted_chunks),
                    },
                )
            except Exception as audit_err:
                logger.warning(f"Failed to record process audit log: {audit_err}")

            logger.info(f"Successfully processed document {document_id} to status READY.")
            return doc_record




        except Exception as err:
            db.rollback()
            # Ensure failed document chunks are evicted from BM25 index to maintain consistency
            try:
                from app.services.retrieval.bm25_index import bm25_index
                bm25_index.remove_document(document_id)
            except Exception as bm25_err:
                logger.error(f"Failed to evict document {document_id} from BM25 on failure: {bm25_err}")

            # Update status to FAILED
            try:
                failed_doc = db.query(Document).filter(Document.id == doc_uuid).first()
                if failed_doc:
                    failed_doc.status = DocumentStatus.FAILED
                    db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update document status to FAILED: {db_err}")

            if isinstance(err, HTTPException):
                raise err
            logger.error(f"Document processing failed for {document_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {str(err)}",
            ) from err

    def is_user_authorized_for_doc(self, user: Optional[Any], doc: Optional[Document]) -> bool:
        """Check if user has permission to access document based on role, access_level, and department."""
        if not doc:
            return False
        doc_access = (doc.access_level or "internal").lower()
        if user is None:
            return doc_access == "public"

        user_roles = [r.name for r in getattr(user, "roles", [])]
        if "admin" in user_roles:
            return True

        doc_dept = doc.department
        user_dept = getattr(user, "department", None)
        user_id = getattr(user, "id", None)

        if "analyst" in user_roles:
            if doc_access in ["public", "internal", "confidential"]:
                if doc_dept is None or doc_dept == user_dept or doc_access == "public":
                    return True
            return False

        # Regular user role
        if doc_access == "public":
            return True
        if doc_access == "internal":
            if doc_dept is None or doc_dept == user_dept or (user_id and getattr(doc, "uploaded_by", None) == user_id):
                return True
        return False

    def list_documents(
        self,
        db: Session,
        user: Optional[Any] = None,
        skip: int = 0,
        limit: int = 50,
        department: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        access_level: Optional[str] = None,
    ) -> List[Document]:
        """List documents with pagination, filters, and authorization rules."""
        from sqlalchemy import or_, and_

        query = db.query(Document)

        # 1. Authorization filters
        if user is None:
            query = query.filter(Document.access_level == "public")
        else:
            user_roles = [r.name for r in getattr(user, "roles", [])]
            user_dept = getattr(user, "department", None)
            user_id = getattr(user, "id", None)

            if "admin" in user_roles:
                pass  # Admin can access all documents
            elif "analyst" in user_roles:
                cond = or_(
                    Document.access_level == "public",
                    and_(
                        Document.access_level.in_(["internal", "confidential"]),
                        or_(Document.department == None, Document.department == user_dept),
                    ),
                )
                query = query.filter(cond)
            else:
                # Regular user
                cond = or_(
                    Document.access_level == "public",
                    and_(
                        Document.access_level == "internal",
                        or_(
                            Document.department == None,
                            Document.department == user_dept,
                            Document.uploaded_by == user_id if user_id else False,
                        ),
                    ),
                    Document.uploaded_by == user_id if user_id else False,
                )
                query = query.filter(cond)

        # 2. Query parameter filters
        if department:
            query = query.filter(Document.department == department)
        if status:
            query = query.filter(Document.status == status)
        if access_level:
            query = query.filter(Document.access_level == access_level.lower())

        return (
            query.order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_document(
        self,
        db: Session,
        document_id: str,
        user: Optional[Any] = None,
    ) -> Tuple[Document, int]:
        """Retrieve single document metadata, validating existence and authorization, with chunk count."""
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document UUID: {document_id}",
            ) from err

        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )

        if not self.is_user_authorized_for_doc(user, doc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this document.",
            )

        from app.models.document_chunk import DocumentChunk
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        return doc, chunk_count

    def delete_document(
        self,
        db: Session,
        document_id: str,
        user: Optional[Any] = None,
    ) -> bool:
        """Delete document end-to-end: verify authorization, remove Qdrant vectors, BM25 index, file storage, and DB records."""
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document UUID: {document_id}",
            ) from err

        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )

        # Authorization: require admin OR uploader
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to delete documents.",
            )

        user_roles = [r.name for r in getattr(user, "roles", [])]
        user_id = getattr(user, "id", None)
        is_admin = "admin" in user_roles
        is_uploader = user_id and doc.uploaded_by == user_id

        if not (is_admin or is_uploader):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only administrators or the document uploader can delete this document.",
            )

        # 1. Delete vector points from Qdrant
        try:
            from app.services.vector_store import qdrant_vector_store
            qdrant_vector_store.delete_vectors_by_document(document_id)
        except Exception as qdrant_err:
            logger.warning(f"Error removing vectors for document {document_id}: {qdrant_err}")

        # 2. Remove from BM25 index
        try:
            from app.services.retrieval.bm25_index import bm25_index
            bm25_index.remove_document(document_id)
        except Exception as bm25_err:
            logger.warning(f"Error removing document {document_id} from BM25: {bm25_err}")

        # 3. Remove physical files from storage
        try:
            self.storage.delete_file_directory(document_id)
        except Exception as file_err:
            logger.warning(f"Error cleaning up storage for document {document_id}: {file_err}")

        # 4. Delete document record (cascade deletes document_chunks)
        db.delete(doc)
        db.commit()

        try:
            from app.services.audit_service import audit_service
            audit_service.log_event(
                db=db,
                action="delete",
                resource_type="document",
                user_id=getattr(user, "id", None),
                resource_id=document_id,
                details={
                    "filename": doc.filename,
                    "department": doc.department,
                },
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record delete audit log: {audit_err}")

        logger.info(f"Successfully deleted document {document_id}")
        return True



document_service = DocumentService()


