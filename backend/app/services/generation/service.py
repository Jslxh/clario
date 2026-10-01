import re
import time
import logging
from typing import Optional, List, Dict, Set, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.retrieval.hybrid_retriever import HybridRetriever, hybrid_retriever
from app.services.retrieval.models import SearchFilters, RetrievalMode
from app.services.context.builder import ContextBuilder, context_builder
from app.services.llm.base import BaseLLMProvider, LLMGenerationRequest
from app.services.llm.factory import llm_provider
from app.services.llm.openai_provider import ContextLengthExceededError
from app.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    SourceCitation,
    ContextChunk,
    BuiltContext,
)

logger = logging.getLogger(__name__)


from app.services.verification import VerificationService, verification_service


class GenerationService:
    """End-to-end Enterprise Question Answering and LLM Generation Service."""

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        context_engine: Optional[ContextBuilder] = None,
        provider: Optional[BaseLLMProvider] = None,
        verifier: Optional[VerificationService] = None,
    ):
        self.retriever = retriever or hybrid_retriever
        self.context_builder = context_engine or context_builder
        self.llm_provider = provider or llm_provider
        self.verifier = verifier or verification_service

    def _extract_and_map_citations(
        self,
        answer_text: str,
        supplied_chunks: List[ContextChunk],
    ) -> tuple[str, List[SourceCitation]]:
        """Extract [Doc-X] tags from answer, map to supplied chunk metadata, and strip unmapped unknown tags."""
        chunk_map = {c.source_index: c for c in supplied_chunks}
        found_tags: Set[int] = set()

        # Find all [Doc-X] references in answer text
        tag_pattern = re.compile(r"\[Doc-(\d+)\]")

        def _replace_or_validate_tag(match: re.Match) -> str:
            idx = int(match.group(1))
            if idx in chunk_map:
                found_tags.add(idx)
                return match.group(0)  # Keep valid tag
            # Unknown tag not in supplied context: strip from answer text
            logger.warning(f"Stripping unmapped/hallucinated citation tag '[Doc-{idx}]' from answer.")
            return ""

        cleaned_answer = tag_pattern.sub(_replace_or_validate_tag, answer_text)
        # Clean up any leftover duplicate whitespaces
        cleaned_answer = re.sub(r" +", " ", cleaned_answer).strip()

        # Build citations for all cited tags in ascending index order
        citations: List[SourceCitation] = []
        for idx in sorted(found_tags):
            chunk = chunk_map[idx]
            citations.append(
                SourceCitation(
                    source_tag=chunk.source_tag,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    end_page=chunk.end_page,
                    section=chunk.section,
                    department=chunk.department,
                    access_level=chunk.access_level,
                    relevance_score=chunk.score,
                )
            )

        # If no explicit citation tags appeared in text but answer was generated from context, include all supplied chunks
        if not citations and supplied_chunks:
            for chunk in supplied_chunks:
                citations.append(
                    SourceCitation(
                        source_tag=chunk.source_tag,
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        filename=chunk.filename,
                        page_number=chunk.page_number,
                        end_page=chunk.end_page,
                        section=chunk.section,
                        department=chunk.department,
                        access_level=chunk.access_level,
                        relevance_score=chunk.score,
                    )
                )

        return cleaned_answer, citations

    def answer_query(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        mode: Optional[RetrievalMode] = None,
        enable_rerank: Optional[bool] = None,
        max_output_tokens: Optional[int] = None,
        verify: Optional[bool] = None,
        user: Optional[Any] = None,
    ) -> GenerationResponse:
        """Execute complete Q&A pipeline: Retrieval -> Context Assembly -> LLM Generation -> Citation Mapping -> Grounding Verification."""
        t0 = time.perf_counter()

        if not query or not query.strip():
            raise ValueError("Query string cannot be empty or whitespace-only.")

        cleaned_query = query.strip()
        effective_top_k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
        effective_mode = mode or RetrievalMode(settings.DEFAULT_RETRIEVAL_MODE)
        effective_max_tokens = max_output_tokens or settings.LLM_MAX_OUTPUT_TOKENS
        effective_verify = verify if verify is not None else settings.VERIFICATION_ENABLED

        # 1. First/Second-Stage Retrieval
        search_resp = self.retriever.search(
            db=db,
            query=cleaned_query,
            top_k=effective_top_k,
            filters=filters,
            mode=effective_mode,
            enable_rerank=enable_rerank,
            user=user,
        )

        candidates = search_resp.results

        # 2. Context Construction & Token Budgeting
        built_context = self.context_builder.build_context(
            query=cleaned_query,
            candidates=candidates,
        )

        # 3. Short-Circuit Abstention on Empty/Insufficient Context
        if not built_context.has_sufficient_context or not built_context.context_chunks:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            verification_result = (
                self.verifier.verify_generation(
                    raw_answer="",
                    context_chunks=[],
                    has_sufficient_context=False,
                )
                if effective_verify
                else None
            )
            return GenerationResponse(
                query=cleaned_query,
                answer="I could not find sufficient information in the provided documentation to answer your question.",
                citations=[],
                has_sufficient_context=False,
                model_name=getattr(self.llm_provider, "model_name", settings.LLM_MODEL_NAME),
                retrieval_mode=effective_mode.value,
                latency_ms=latency_ms,
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                verification=verification_result,
            )

        # 4. LLM Generation with Context Length Recovery
        gen_req = LLMGenerationRequest(
            system_prompt=built_context.system_prompt,
            user_prompt=built_context.user_prompt,
            temperature=settings.LLM_TEMPERATURE,  # Fixed 0.0
            max_output_tokens=effective_max_tokens,
        )

        try:
            llm_resp = self.llm_provider.generate(gen_req)
        except ContextLengthExceededError:
            logger.warning("LLM provider rejected context length. Deterministically dropping lowest chunk and retrying once.")
            built_context = self.context_builder.rebuild_with_reduced_chunks(built_context, query=cleaned_query)
            gen_req.user_prompt = built_context.user_prompt
            llm_resp = self.llm_provider.generate(gen_req)

        # 5. Optional Grounding & Faithfulness Verification on Raw LLM Output
        verification_result = None
        if effective_verify:
            verification_result = self.verifier.verify_generation(
                raw_answer=llm_resp.content,
                context_chunks=built_context.context_chunks,
                has_sufficient_context=built_context.has_sufficient_context,
            )

        # 6. Citation Extraction and Public Answer Sanitization
        cleaned_answer, citations = self._extract_and_map_citations(
            answer_text=llm_resp.content,
            supplied_chunks=built_context.context_chunks,
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return GenerationResponse(
            query=cleaned_query,
            answer=cleaned_answer,
            citations=citations,
            has_sufficient_context=True,
            model_name=llm_resp.model_name,
            retrieval_mode=effective_mode.value,
            latency_ms=latency_ms,
            token_usage={
                "prompt_tokens": llm_resp.prompt_tokens,
                "completion_tokens": llm_resp.completion_tokens,
                "total_tokens": llm_resp.total_tokens,
            },
            verification=verification_result,
        )


generation_service = GenerationService()
