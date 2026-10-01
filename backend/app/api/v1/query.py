import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation import generation_service
from app.services.llm.openai_provider import AuthenticationError, LLMProviderError

from app.api.deps import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query & Generation"])


@router.post(
    "",
    response_model=GenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Enterprise RAG Question Answering",
    description=(
        "Synthesize grounded enterprise answers from verified document context using hybrid retrieval, "
        "Cross-Encoder reranking, deterministic LLM generation, and optional Grounding & Faithfulness Verification. "
        "Enforces document access permissions and department boundaries based on user identity."
    ),
)
def query_documents(
    request: GenerationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        return generation_service.answer_query(
            db=db,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            mode=request.mode,
            enable_rerank=request.enable_rerank,
            max_output_tokens=request.max_output_tokens,
            verify=request.verify,
            user=current_user,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except AuthenticationError as auth_err:
        logger.error(f"LLM Provider authentication failure: {auth_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM provider authentication error. Please verify backend provider credentials.",
        ) from auth_err
    except LLMProviderError as prov_err:
        logger.error(f"LLM Provider error: {prov_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Downstream LLM provider error: {prov_err}",
        ) from prov_err
    except Exception as err:
        logger.error(f"Unexpected error in query generation pipeline: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during question answering generation.",
        ) from err
