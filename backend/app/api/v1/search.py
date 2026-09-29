import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.retrieval import (
    SearchRequest,
    SearchResponse,
    semantic_retriever,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Document Chunk Search",
    description=(
        "Perform vector similarity search over enterprise document chunks using BGE embeddings. "
        "Returns top-K candidate chunks hydrated with canonical content from PostgreSQL. "
        "Note: Similarity scores represent raw Cosine vector similarity, not confidence percentages or probabilities. "
        "The current semantic search endpoint is a retrieval foundation and does not enforce an authorization boundary. "
        "Enterprise authorization and Role-Based Access Control (RBAC) will be added before production user access."
    ),
)
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    try:
        return semantic_retriever.search(
            db=db,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error(f"Semantic search failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during semantic retrieval.",
        ) from err
