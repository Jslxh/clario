import logging

from app.services.parsers.base import BaseParser
from app.schemas.parser import ParsedDocument, ParsedPage
from app.core.exceptions import CorruptFileError

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """Parser for reading plain text files safely with UTF-8 and fallback encoding."""

    def parse(self, file_path: str, document_id: str, filename: str) -> ParsedDocument:
        content = ""
        # Try UTF-8 first, fallback to latin-1 for legacy text encodings
        for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as err:
                logger.error(f"Failed to read TXT file '{filename}': {err}")
                raise CorruptFileError(f"File '{filename}' is unreadable.", document_type="txt") from err

        has_usable_text = bool(content.strip())

        pages = [
            ParsedPage(
                page_number=1,
                text=content,
                sections=[],
            )
        ]

        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            document_type="txt",
            has_usable_text=has_usable_text,
            total_pages=1,
            pages=pages,
            metadata={"character_count": len(content)},
        )
