import logging
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.parsers.base import BaseParser
from app.schemas.parser import ParsedDocument, ParsedPage
from app.core.exceptions import CorruptFileError, NoExtractableTextError

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """Parser for extracting normalized text content from PDF documents while preserving page boundaries."""

    def parse(self, file_path: str, document_id: str, filename: str) -> ParsedDocument:
        try:
            reader = PdfReader(file_path)
        except (PdfReadError, Exception) as err:
            logger.error(f"Failed to read PDF file '{filename}': {err}")
            raise CorruptFileError(f"File '{filename}' is corrupt or not a valid PDF.", document_type="pdf") from err

        pages = []
        total_extracted_chars = 0

        for index, page in enumerate(reader.pages):
            page_num = index + 1
            page_text = ""
            try:
                extracted = page.extract_text()
                if extracted:
                    page_text = extracted.strip()
            except Exception as page_err:
                logger.warning(f"Error extracting text from page {page_num} of '{filename}': {page_err}")

            pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=page_text,
                    sections=[],
                )
            )
            total_extracted_chars += len(page_text)

        has_usable_text = total_extracted_chars > 0

        metadata = {
            "is_encrypted": reader.is_encrypted,
            "total_extracted_characters": total_extracted_chars,
        }

        if not has_usable_text:
            metadata["parsing_note"] = "PDF contains no extractable text (image-only or scanned document)."

        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            document_type="pdf",
            has_usable_text=has_usable_text,
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
        )
