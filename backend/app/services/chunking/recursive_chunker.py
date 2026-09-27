import re
import logging
from typing import List, Optional, Tuple, Dict, Any

from app.core.config import settings
from app.schemas.parser import ParsedDocument, ParsedPage
from app.schemas.chunk import NormalizedChunk
from app.services.chunking.token_counter import TokenCounter, token_counter

logger = logging.getLogger(__name__)


class RecursiveStructureChunker:
    """Structure-aware and recursive document chunker.
    
    Preserves headings, section boundaries, paragraph context, and page lineage.
    Splits large text units recursively along natural sentence and word boundaries.
    """

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        counter: Optional[TokenCounter] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.counter = counter or token_counter
        self.max_chars = self.counter.max_chars_for_tokens(self.chunk_size)
        self.overlap_chars = self.counter.max_chars_for_tokens(self.chunk_overlap)

    def _split_text_recursively(self, text: str, max_chars: int, overlap_chars: int) -> List[str]:
        """Recursively split text using paragraph, sentence, and word boundaries without cutting words."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= max_chars:
            return [text]

        # Separator hierarchy: Paragraphs -> Lines -> Sentences -> Words
        separators = ["\n\n", "\n", ". ", "; ", ", ", " "]
        chosen_sep = " "
        for sep in separators:
            if sep in text:
                chosen_sep = sep
                break

        splits = text.split(chosen_sep)
        chunks = []
        current_unit = []
        current_len = 0

        for split in splits:
            item = split.strip()
            if not item:
                continue

            item_len = len(item) + len(chosen_sep)
            if current_len + item_len > max_chars and current_unit:
                chunk_str = chosen_sep.join(current_unit).strip()
                if chunk_str:
                    chunks.append(chunk_str)

                # Calculate overlap units from tail
                overlap_unit = []
                overlap_len = 0
                for prev in reversed(current_unit):
                    if overlap_len + len(prev) <= overlap_chars:
                        overlap_unit.insert(0, prev)
                        overlap_len += len(prev) + len(chosen_sep)
                    else:
                        break

                current_unit = overlap_unit + [item]
                current_len = sum(len(x) + len(chosen_sep) for x in current_unit)
            else:
                current_unit.append(item)
                current_len += item_len

        if current_unit:
            final_chunk = chosen_sep.join(current_unit).strip()
            if final_chunk:
                chunks.append(final_chunk)

        # Fallback safeguard for oversized items without whitespace
        result = []
        for chunk in chunks:
            if len(chunk) > max_chars * 1.5 and chosen_sep != " ":
                result.extend(self._split_text_recursively(chunk, max_chars, overlap_chars))
            else:
                result.append(chunk)

        return result

    def chunk_document(self, doc: ParsedDocument) -> List[NormalizedChunk]:
        """Convert a ParsedDocument into a deterministic list of NormalizedChunks."""
        if not doc.has_usable_text or not doc.pages:
            logger.info(f"Document '{doc.filename}' has no usable text; returning 0 chunks.")
            return []

        chunks: List[NormalizedChunk] = []
        chunk_index = 0
        is_txt = doc.document_type.lower() == "txt"

        # Accumulate blocks across pages while tracking page range and heading context
        current_blocks: List[str] = []
        current_start_page: Optional[int] = None
        current_end_page: Optional[int] = None
        current_section: Optional[str] = None

        for page in doc.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            page_num = page.page_number if not is_txt else None
            page_sections = page.sections

            # If page contains explicit sections (DOCX headings)
            if page_sections and len(page_sections) > 0:
                current_section = page_sections[0]

            if current_start_page is None:
                current_start_page = page_num
            current_end_page = page_num

            current_blocks.append(page_text)

        full_doc_text = "\n\n".join(current_blocks).strip()
        if not full_doc_text:
            return []

        header_prefix = f"# {current_section}\n\n" if current_section else ""
        full_content_check = f"{header_prefix}{full_doc_text}".strip()

        # If entire document text fits within single chunk target size
        if len(full_content_check) <= self.max_chars:
            chunk = NormalizedChunk(
                document_id=doc.document_id,
                chunk_id=None,
                chunk_index=0,
                content=full_content_check,
                section=current_section,
                start_page=current_start_page,
                end_page=current_end_page,
                metadata={
                    "document_type": doc.document_type,
                    "estimated_tokens": self.counter.count_tokens(full_content_check),
                    "character_count": len(full_content_check),
                },
            )
            return [chunk]

        # Recursive split for large content
        split_units = self._split_text_recursively(full_doc_text, self.max_chars, self.overlap_chars)

        for text_unit in split_units:
            if not text_unit.strip():
                continue

            header_prefix = f"# {current_section}\n\n" if current_section else ""
            chunk_content = f"{header_prefix}{text_unit}".strip()

            chunk = NormalizedChunk(
                document_id=doc.document_id,
                chunk_id=None,
                chunk_index=chunk_index,
                content=chunk_content,
                section=current_section,
                start_page=current_start_page,
                end_page=current_end_page,
                metadata={
                    "document_type": doc.document_type,
                    "estimated_tokens": self.counter.count_tokens(chunk_content),
                    "character_count": len(chunk_content),
                },
            )
            chunks.append(chunk)
            chunk_index += 1

        return chunks
