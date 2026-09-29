import uuid
import logging
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import BaseEmbeddingService, embedding_service
from app.services.vector_store import BaseVectorStore, qdrant_vector_store
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.models import SearchFilters, RetrievalResult, SearchResponse

logger = logging.getLogger(__name__)


class SemanticRetriever(BaseRetriever):
    """Semantic document retriever combining BGE embeddings, Qdrant vector search, and PostgreSQL hydration."""

    def __init__(
        self,
        embedder: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
    ):
        self.embedder = embedder or embedding_service
        self.vector_store = vector_store or qdrant_vector_store

    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
    ) -> SearchResponse:
        """Execute semantic similarity search for a query and return hydrated candidate chunks.
        
        Args:
            db: SQLAlchemy database session.
            query: User search query string (non-empty).
            top_k: Number of candidate chunks to retrieve (default from config).
            filters: Optional metadata filters.
            
        Returns:
            SearchResponse containing query, total_results, and ordered RetrievalResult items.
        """
        # 1. Query Validation
        if not query or not query.strip():
            err_msg = "Query string cannot be empty or whitespace-only."
            logger.error(err_msg)
            raise ValueError(err_msg)

        cleaned_query = query.strip()

        # 2. top_k Validation
        effective_top_k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
        if effective_top_k <= 0:
            err_msg = f"top_k must be a positive integer > 0, got {effective_top_k}."
            logger.error(err_msg)
            raise ValueError(err_msg)

        if effective_top_k > settings.RETRIEVAL_MAX_TOP_K:
            err_msg = (
                f"top_k value ({effective_top_k}) exceeds maximum allowed limit "
                f"of {settings.RETRIEVAL_MAX_TOP_K}."
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

        # 3. Generate query embedding
        query_vector = self.embedder.embed_query(cleaned_query)

        # 4. Extract filters if present
        filter_dict = filters.model_dump(exclude_none=True) if filters else None

        # 5. Qdrant vector similarity search
        vector_matches = self.vector_store.search_vectors(
            query_vector=query_vector,
            top_k=effective_top_k,
            filters=filter_dict,
        )

        if not vector_matches:
            logger.info(f"No vector matches found in Qdrant for query: '{cleaned_query}'")
            return SearchResponse(query=cleaned_query, total_results=0, results=[])

        # 6. Extract candidate chunk UUIDs
        chunk_uuids: List[uuid.UUID] = []
        for match in vector_matches:
            cid = match.get("point_id")
            try:
                if cid:
                    chunk_uuids.append(uuid.UUID(str(cid)))
            except ValueError:
                logger.warning(f"Vector match point ID '{cid}' is not a valid UUID string. Skipping.")

        if not chunk_uuids:
            return SearchResponse(query=cleaned_query, total_results=0, results=[])

        # 7. PostgreSQL Single-Query Hydration (Eager loading document relationship to prevent N+1 queries)
        db_chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(chunk_uuids))
            .all()
        )

        chunk_map = {str(chunk.id): chunk for chunk in db_chunks}

        # 8. Construct RetrievalResults maintaining exact Qdrant vector rank order
        results: List[RetrievalResult] = []
        for match in vector_matches:
            point_id = match["point_id"]
            score = match["score"]
            payload = match.get("payload", {})

            db_chunk = chunk_map.get(point_id)
            if not db_chunk:
                logger.warning(
                    f"Chunk ID '{point_id}' returned by vector index was not found in PostgreSQL. Skipping missing chunk."
                )
                continue

            doc = db_chunk.document
            results.append(
                RetrievalResult(
                    chunk_id=str(db_chunk.id),
                    document_id=str(doc.id) if doc else payload.get("document_id", ""),
                    score=score,
                    content=db_chunk.content,  # Canonical content from PostgreSQL
                    page_number=db_chunk.page_number,
                    end_page=db_chunk.end_page,
                    section=db_chunk.section,
                    filename=doc.filename if doc else payload.get("filename", ""),
                    document_type=doc.document_type if doc else payload.get("document_type", ""),
                    department=doc.department if doc else payload.get("department"),
                    access_level=doc.access_level if doc else payload.get("access_level", "internal"),
                )
            )

        logger.info(
            f"Successfully retrieved {len(results)} hydrated candidate chunks for query: '{cleaned_query}'"
        )
        return SearchResponse(
            query=cleaned_query,
            total_results=len(results),
            results=results,
        )


semantic_retriever = SemanticRetriever()
