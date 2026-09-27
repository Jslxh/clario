from abc import ABC, abstractmethod
from app.schemas.parser import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for format-specific document parsers."""

    @abstractmethod
    def parse(self, file_path: str, document_id: str, filename: str) -> ParsedDocument:
        """Parse document at file_path into normalized ParsedDocument representation."""
        pass
