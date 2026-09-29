import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.models import (
    SearchFilters,
    RetrievalResult,
    SearchResponse,
    RetrievalMode,
)
from app.services.retrieval.semantic_retriever import SemanticRetriever, semantic_retriever
from app.services.retrieval.bm25_index import BM25Index, bm25_index
from app.services.retrieval.fusion import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Hybrid document retriever orchestrating semantic search, BM25 keyword search, and RRF fusion."""

    def __init__(
        self,
        semantic: Optional[SemanticRetriever] = None,
        bm25: Optional[BM25Index] = None,
        rrf_k: Optional[int] = None,
    ):
        self.semantic_retriever = semantic or semantic_retriever
        self.bm25_index = bm25 or bm25_index
        self.rrf_k = rrf_k or settings.RRF_K

    def _hydrate_results(
        self,
        db: Session,
        candidate_matches: List[Dict[str, Any]],
    ) -> List[RetrievalResult]:
        """Perform single batched SQL query to hydrate canonical content and metadata for candidate chunk IDs."""
        if not candidate_matches:
            return []

        chunk_uuids: List[uuid.UUID] = []
        for match in candidate_matches:
            cid = match.get("point_id")
            try:
                if cid:
                    chunk_uuids.append(uuid.UUID(str(cid)))
            except ValueError:
                logger.warning(f"Candidate match point ID '{cid}' is not a valid UUID string. Skipping.")

        if not chunk_uuids:
            return []

        # Single batched SQL query eager-loading document relationship (prevents N+1)
        db_chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(chunk_uuids))
            .all()
        )

        chunk_map = {str(chunk.id): chunk for chunk in db_chunks}

        results: List[RetrievalResult] = []
        for match in candidate_matches:
            point_id = match["point_id"]
            score = match["score"]
            payload = match.get("payload", {})

            db_chunk = chunk_map.get(point_id)
            if not db_chunk:
                logger.warning(
                    f"Candidate chunk ID '{point_id}' was not found in PostgreSQL database. Skipping missing chunk."
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

        return results

    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        mode: Optional[RetrievalMode] = None,
    ) -> SearchResponse:
        """Execute search in hybrid, semantic-only, or BM25-only mode.
        
        Args:
            db: Active SQLAlchemy database session.
            query: Non-empty query string.
            top_k: Max candidate results to return (default 5, max 100).
            filters: Optional metadata filters (department, document_type, access_level, document_id).
            mode: Retrieval mode ('hybrid', 'semantic', 'bm25'). Defaults to config DEFAULT_RETRIEVAL_MODE.
            
        Returns:
            SearchResponse containing ranked and hydrated results.
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

        # 3. Resolve Mode
        effective_mode = mode or RetrievalMode(settings.DEFAULT_RETRIEVAL_MODE)

        # Mode A: Semantic-Only Baseline
        if effective_mode == RetrievalMode.SEMANTIC:
            resp = self.semantic_retriever.search(
                db=db,
                query=cleaned_query,
                top_k=effective_top_k,
                filters=filters,
            )
            resp.mode = "semantic"
            return resp

        # Mode B: BM25-Only Keyword Retrieval
        if effective_mode == RetrievalMode.BM25:
            self.bm25_index.ensure_initialized(db)
            bm25_candidates = self.bm25_index.search(
                query=cleaned_query,
                top_k=effective_top_k,
                filters=filters,
            )
            results = self._hydrate_results(db=db, candidate_matches=bm25_candidates)
            return SearchResponse(
                query=cleaned_query,
                mode="bm25",
                total_results=len(results),
                results=results,
            )

        # Mode C: Hybrid Retrieval (Semantic + BM25 + Reciprocal Rank Fusion)
        self.bm25_index.ensure_initialized(db)

        # Retrieve candidates from both sources (pool larger than top_k for optimal fusion depth)
        candidate_pool_size = max(effective_top_k * 2, 20)

        # 1. Semantic candidates
        filter_dict = filters.model_dump(exclude_none=True) if filters else None
        query_vector = self.semantic_retriever.embedder.embed_query(cleaned_query)
        semantic_matches = self.semantic_retriever.vector_store.search_vectors(
            query_vector=query_vector,
            top_k=candidate_pool_size,
            filters=filter_dict,
        )

        # 2. BM25 keyword candidates
        bm25_matches = self.bm25_index.search(
            query=cleaned_query,
            top_k=candidate_pool_size,
            filters=filters,
        )

        # 3. Reciprocal Rank Fusion
        fused_candidates = reciprocal_rank_fusion(
            ranked_lists={
                "semantic": semantic_matches,
                "bm25": bm25_matches,
            },
            k=self.rrf_k,
            top_k=effective_top_k,
        )

        fused_dicts = [
            {
                "point_id": fc.point_id,
                "score": fc.rrf_score,
                "payload": fc.payload,
            }
            for fc in fused_candidates
        ]

        # 4. PostgreSQL Single-Query Hydration
        results = self._hydrate_results(db=db, candidate_matches=fused_dicts)

        logger.info(
            f"Hybrid search returned {len(results)} fused candidate chunks for query: '{cleaned_query}'"
        )
        return SearchResponse(
            query=cleaned_query,
            mode="hybrid",
            total_results=len(results),
            results=results,
        )


hybrid_retriever = HybridRetriever()
