from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingService(ABC):
    """Abstract base class for document and query embedding services."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embeddings for a list of document chunk texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate a normalized embedding for a search query."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the expected vector dimension."""
        pass
