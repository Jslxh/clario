import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.retrieval import (
    SearchRequest,
    SearchResponse,
    hybrid_retriever,
)
from app.api.deps import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid Enterprise Document Search",
    description=(
        "Perform enterprise document search combining BGE semantic vector similarity, "
        "BM25 keyword search, Reciprocal Rank Fusion (RRF), and Cross-Encoder neural reranking. "
        "Supports configurable retrieval modes ('hybrid', 'semantic', 'bm25') and optional reranking toggle with canonical content hydrated from PostgreSQL. "
        "Enforces document access permissions and department boundaries based on user identity."
    ),
)
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        return hybrid_retriever.search(
            db=db,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            mode=request.mode,
            enable_rerank=request.enable_rerank,
            user=current_user,
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

