from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session
from app.services.retrieval.models import SearchFilters, SearchResponse


class BaseRetriever(ABC):
    """Abstract base class for document retrieval services."""

    @abstractmethod
    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = 5,
        filters: Optional[SearchFilters] = None,
    ) -> SearchResponse:
        """Perform document retrieval for a user query."""
        pass
