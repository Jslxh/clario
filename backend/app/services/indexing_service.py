import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import BaseEmbeddingService, embedding_service
from app.services.vector_store import BaseVectorStore, qdrant_vector_store

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Service orchestrating batch embedding generation and Qdrant vector store indexing."""

    def __init__(
        self,
        embedder: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
    ):
        self.embedder = embedder or embedding_service
        self.vector_store = vector_store or qdrant_vector_store

    def index_document_chunks(self, db: Session, document_id: str) -> Dict[str, Any]:
        """Load persisted chunks from PostgreSQL, generate embeddings, and upsert vectors to Qdrant.
        
        Args:
            db: Active SQLAlchemy database session.
            document_id: UUID string of target document.
            
        Returns:
            Dictionary containing indexing summary statistics.
        """
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as err:
            raise ValueError(f"Invalid document UUID string: {document_id}") from err

        # 1. Fetch parent document record
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            err_msg = f"Document with ID {document_id} not found."
            logger.error(err_msg)
            raise ValueError(err_msg)

        # 2. Fetch document chunks ordered by chunk index
        db_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc_uuid)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

        if not db_chunks:
            logger.warning(f"No persisted chunks found in database for document {document_id}.")
            return {
                "document_id": document_id,
                "indexed_chunks": 0,
                "status": "no_chunks",
            }

        # 3. Batch generate embeddings for chunk contents
        chunk_texts = [chunk.content for chunk in db_chunks]
        embeddings = self.embedder.embed_documents(chunk_texts)

        if len(embeddings) != len(db_chunks):
            raise RuntimeError(
                f"Embedding count mismatch for doc {document_id}: "
                f"expected {len(db_chunks)}, generated {len(embeddings)}"
            )

        # 4. Construct point payload objects
        points_to_upsert: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(db_chunks):
            vector = embeddings[idx]
            payload = {
                "document_id": str(document.id),
                "chunk_id": str(chunk.id),
                "page_number": chunk.page_number,
                "end_page": chunk.end_page,
                "section": chunk.section,
                "department": document.department,
                "document_type": document.document_type,
                "access_level": document.access_level,
                "filename": document.filename,
            }
            points_to_upsert.append({
                "point_id": str(chunk.id),
                "vector": vector,
                "payload": payload,
            })

        # 5. Upsert points to vector store
        self.vector_store.upsert_vectors(points_to_upsert)

        logger.info(f"Successfully indexed {len(points_to_upsert)} chunk vectors for document {document_id}.")
        return {
            "document_id": document_id,
            "indexed_chunks": len(points_to_upsert),
            "status": "success",
        }


indexing_service = DocumentIndexingService()
