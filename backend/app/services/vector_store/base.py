from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseVectorStore(ABC):
    """Abstract base class for vector store operations."""

    @abstractmethod
    def verify_collection(self) -> bool:
        """Verify that the target vector collection exists and is ready."""
        pass

    @abstractmethod
    def upsert_vectors(self, points: List[Dict[str, Any]]) -> bool:
        """Upsert points (ID, vector, payload) into vector storage idempotently."""
        pass
