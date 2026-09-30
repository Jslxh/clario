import logging
import threading
from typing import List, Optional
import numpy as np

from app.core.config import settings
from app.services.retrieval.models import RetrievalResult
from app.services.reranking.base import BaseReranker

logger = logging.getLogger(__name__)


class CrossEncoderReranker(BaseReranker):
    """Second-stage neural reranker using HuggingFace CrossEncoder models.
    
    Defaults to 'cross-encoder/ms-marco-MiniLM-L-6-v2'.
    Performs full cross-attention over (query, chunk_content) pairs to compute
    fine-grained relevance scores and reorder first-stage candidate chunks.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        device: Optional[str] = None,
        fallback_on_error: Optional[bool] = None,
    ):
        self.model_name = model_name or settings.RERANKING_MODEL_NAME
        self.batch_size = batch_size or settings.RERANKING_BATCH_SIZE
        self.device_setting = device or settings.RERANKING_DEVICE
        self.fallback_on_error = (
            fallback_on_error
            if fallback_on_error is not None
            else settings.RERANKING_FALLBACK_ON_ERROR
        )

        self._lock = threading.RLock()
        self._model = None

    def _resolve_device(self) -> str:
        """Resolve 'auto' device setting to 'cuda' if GPU is available, otherwise 'cpu'."""
        if self.device_setting == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return self.device_setting

    def _get_model(self):
        """Lazy load and cache the CrossEncoder model instance with double-checked locking."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    resolved_device = self._resolve_device()
                    logger.info(
                        f"Loading cross-encoder reranking model '{self.model_name}' on device '{resolved_device}'..."
                    )
                    try:
                        from sentence_transformers import CrossEncoder
                        self._model = CrossEncoder(self.model_name, device=resolved_device)
                    except Exception as err:
                        logger.error(
                            f"Failed to load cross-encoder model '{self.model_name}': {err}"
                        )
                        raise RuntimeError(
                            f"CrossEncoder model loading failed for '{self.model_name}': {err}"
                        ) from err
        return self._model

    def is_model_loaded(self) -> bool:
        """Check if the underlying cross-encoder model has been loaded into memory."""
        with self._lock:
            return self._model is not None

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Rerank first-stage candidate chunks using the cross-encoder model.
        
        Preserves first-stage score and rank on each candidate before sorting
        descending by the cross-encoder logit.
        """
        if not candidates:
            return []

        cleaned_query = query.strip() if query else ""
        if not cleaned_query:
            return candidates[:top_k] if top_k is not None else candidates

        # Construct (query, text) sentence pairs for cross-attention
        pairs = [(cleaned_query, candidate.content) for candidate in candidates]

        try:
            model = self._get_model()
            raw_scores = model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            if isinstance(raw_scores, (int, float, np.floating)):
                scores_list = [float(raw_scores)]
            elif isinstance(raw_scores, np.ndarray):
                scores_list = [float(s) for s in raw_scores.tolist()]
            else:
                scores_list = [float(s) for s in raw_scores]

            annotated_candidates: List[RetrievalResult] = []
            for idx, (candidate, score_val) in enumerate(zip(candidates, scores_list)):
                annotated = RetrievalResult(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    score=score_val,
                    content=candidate.content,
                    page_number=candidate.page_number,
                    end_page=candidate.end_page,
                    section=candidate.section,
                    filename=candidate.filename,
                    document_type=candidate.document_type,
                    department=candidate.department,
                    access_level=candidate.access_level,
                    initial_score=candidate.score,
                    initial_rank=idx + 1,
                    rerank_score=score_val,
                )
                annotated_candidates.append(annotated)

            # Sort descending by rerank_score with deterministic tie-breaking on chunk_id
            annotated_candidates.sort(
                key=lambda c: (-c.rerank_score if c.rerank_score is not None else float("-inf"), c.chunk_id)
            )

            if top_k is not None and top_k > 0:
                return annotated_candidates[:top_k]
            return annotated_candidates

        except Exception as err:
            logger.error(f"Cross-encoder reranking failed for query '{query}': {err}")
            if self.fallback_on_error:
                logger.warning("Falling back to first-stage retrieval candidate ordering.")
                fallback_results = []
                for idx, c in enumerate(candidates):
                    fallback_item = RetrievalResult(
                        chunk_id=c.chunk_id,
                        document_id=c.document_id,
                        score=c.score,
                        content=c.content,
                        page_number=c.page_number,
                        end_page=c.end_page,
                        section=c.section,
                        filename=c.filename,
                        document_type=c.document_type,
                        department=c.department,
                        access_level=c.access_level,
                        initial_score=c.score,
                        initial_rank=idx + 1,
                        rerank_score=None,
                    )
                    fallback_results.append(fallback_item)
                if top_k is not None and top_k > 0:
                    return fallback_results[:top_k]
                return fallback_results
            raise RuntimeError(f"CrossEncoder reranking execution failed: {err}") from err


reranker_service = CrossEncoderReranker()
