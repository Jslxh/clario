import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.retrieval import (
    SearchRequest,
    SearchResponse,
    hybrid_retriever,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid Enterprise Document Search",
    description=(
        "Perform hybrid retrieval over enterprise document chunks combining BGE semantic vector similarity, "
        "BM25 keyword search, and Reciprocal Rank Fusion (RRF). "
        "Supports configurable retrieval modes ('hybrid', 'semantic', 'bm25') with canonical content hydrated from PostgreSQL. "
        "Note: Ranking scores represent RRF / similarity / keyword scores, not confidence percentages or probabilities. "
        "The current search endpoint is a retrieval foundation and does not enforce an authorization boundary. "
        "Enterprise authorization and Role-Based Access Control (RBAC) will be added before production user access."
    ),
)
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    try:
        return hybrid_retriever.search(
            db=db,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            mode=request.mode,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error(f"Hybrid retrieval failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during document retrieval.",
        ) from err

