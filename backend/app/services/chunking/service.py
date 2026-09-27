import uuid
import logging
from typing import List
from sqlalchemy.orm import Session

from app.schemas.parser import ParsedDocument
from app.schemas.chunk import NormalizedChunk
from app.models.document_chunk import DocumentChunk
from app.services.chunking.recursive_chunker import RecursiveStructureChunker

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service handling document chunking and transactional database persistence."""

    def __init__(self, chunker=None):
        self.chunker = chunker or RecursiveStructureChunker()

    def chunk_document(self, doc: ParsedDocument) -> List[NormalizedChunk]:
        """Convert ParsedDocument into normalized chunks using active chunking strategy."""
        return self.chunker.chunk_document(doc)

    def persist_chunks(
        self,
        db: Session,
        document_id: str,
        chunks: List[NormalizedChunk],
    ) -> List[DocumentChunk]:
        """Persist chunks to PostgreSQL document_chunks table with transaction safety and duplicate prevention."""
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as err:
            raise ValueError(f"Invalid document UUID format: {document_id}") from err

        # 1. Clean transaction replacement: remove any existing chunks for this document
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete(synchronize_session=False)

        db_chunks: List[DocumentChunk] = []

        # 2. Insert new chunks
        for idx, chunk in enumerate(chunks):
            chunk_uuid = uuid.uuid4()
            chunk.chunk_id = str(chunk_uuid)
            chunk.chunk_index = idx

            db_record = DocumentChunk(
                id=chunk_uuid,
                document_id=doc_uuid,
                chunk_index=idx,
                content=chunk.content,
                page_number=chunk.start_page,
                end_page=chunk.end_page,
                section=chunk.section,
            )
            db.add(db_record)
            db_chunks.append(db_record)

        db.commit()
        for db_c in db_chunks:
            db.refresh(db_c)

        logger.info(f"Successfully persisted {len(db_chunks)} chunks for document {document_id}")
        return db_chunks


chunking_service = ChunkingService()
