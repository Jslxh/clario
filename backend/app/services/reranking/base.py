from abc import ABC, abstractmethod
from typing import List, Optional

from app.services.retrieval.models import RetrievalResult


class BaseReranker(ABC):
    """Abstract base protocol for second-stage candidate chunk reranking."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Rerank a list of retrieved candidate chunks with respect to a query.
        
        Args:
            query: Non-empty query string.
            candidates: List of hydrated RetrievalResult candidate items from first-stage retrieval.
            top_k: Number of top reranked results to return (if None, returns all).
            
        Returns:
            List of RetrievalResult objects sorted descending by reranker score.
        """
        pass
