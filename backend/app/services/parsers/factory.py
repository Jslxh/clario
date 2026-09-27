import logging
from typing import Dict, Type

from app.services.parsers.base import BaseParser
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.txt_parser import TXTParser
from app.schemas.parser import ParsedDocument
from app.core.exceptions import UnsupportedParserError

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory and dispatch mechanism for resolving format-specific document parsers."""

    _parsers: Dict[str, Type[BaseParser]] = {
        "pdf": PDFParser,
        "docx": DOCXParser,
        "txt": TXTParser,
    }

    @classmethod
    def get_parser(cls, document_type: str) -> BaseParser:
        """Instantiate parser matching the specified document_type extension."""
        normalized_type = document_type.lstrip(".").lower()
        parser_cls = cls._parsers.get(normalized_type)
        if not parser_cls:
            raise UnsupportedParserError(
                f"No parser available for document type '.{normalized_type}'. Supported types: PDF, DOCX, TXT.",
                document_type=normalized_type,
            )
        return parser_cls()

    @classmethod
    def parse_document(
        cls,
        file_path: str,
        document_id: str,
        filename: str,
        document_type: str,
    ) -> ParsedDocument:
        """Parse document using appropriate format parser."""
        parser = cls.get_parser(document_type)
        return parser.parse(file_path, document_id, filename)
