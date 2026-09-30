import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation import generation_service
from app.services.llm.openai_provider import AuthenticationError, LLMProviderError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query & Generation"])


@router.post(
    "",
    response_model=GenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Enterprise RAG Question Answering",
    description=(
        "Synthesize grounded enterprise answers from verified document context using hybrid retrieval, "
        "Cross-Encoder reranking, and deterministic LLM generation. "
        "Returns synthesized answer text, mapped source citations, and operational context indicators. "
        "Note: This endpoint provides syntactic citation mappings and retrieval predicates; "
        "factual NLI grounding validation and enterprise RBAC authorization boundaries are established in subsequent phases."
    ),
)
def query_documents(
    request: GenerationRequest,
    db: Session = Depends(get_db),
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
