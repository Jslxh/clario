from abc import ABC, abstractmethod
from typing import List

from app.schemas.parser import ParsedDocument
from app.schemas.chunk import NormalizedChunk


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    @abstractmethod
    def chunk_document(self, doc: ParsedDocument) -> List[NormalizedChunk]:
        """Convert a ParsedDocument into a list of NormalizedChunks."""
        pass
