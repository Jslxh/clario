import re
import uuid
import logging
import threading
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from dataclasses import dataclass
from sqlalchemy.orm import Session, joinedload
from rank_bm25 import BM25Okapi

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.retrieval.models import SearchFilters

logger = logging.getLogger(__name__)


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercased alphanumeric words and hyphenated technical identifiers.
    
    Handles empty, whitespace-only, or punctuation-only strings safely by returning an empty list.
    """
    if not text:
        return []
    return re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*", text.lower())


@dataclass
class BM25ChunkRecord:
    chunk_id: str
    document_id: str
    content: str
    tokens: List[str]
    department: Optional[str]
    document_type: str
    access_level: str
    page_number: Optional[int]
    end_page: Optional[int]
    section: Optional[str]
    filename: str


class BM25Index:
    """Thread-safe, rebuildable BM25 keyword index over canonical PostgreSQL document chunks."""

    def __init__(self):
        self._lock = threading.RLock()
        self._chunks: Dict[str, BM25ChunkRecord] = {}
        self._doc_to_chunks: Dict[str, Set[str]] = defaultdict(set)
        self._ordered_chunk_ids: List[str] = []
        self._bm25: Optional[BM25Okapi] = None
        self._is_initialized: bool = False

    def _rebuild_model_locked(self) -> None:
        """Internal helper to rebuild the BM25Okapi instance from current active chunks."""
        self._ordered_chunk_ids = list(self._chunks.keys())
        if not self._ordered_chunk_ids:
            self._bm25 = None
            return

        corpus_tokens = [self._chunks[cid].tokens for cid in self._ordered_chunk_ids]
        # Guard against corpus of entirely empty tokens
        if not any(corpus_tokens):
            self._bm25 = None
            return

        self._bm25 = BM25Okapi(corpus_tokens)

    def is_initialized(self) -> bool:
        with self._lock:
            return self._is_initialized

    def size(self) -> int:
        with self._lock:
            return len(self._chunks)

    def clear(self) -> None:
        """Clear all in-memory index structures."""
        with self._lock:
            self._chunks.clear()
            self._doc_to_chunks.clear()
            self._ordered_chunk_ids.clear()
            self._bm25 = None
            self._is_initialized = False

    def invalidate(self) -> None:
        """Mark index as uninitialized so it will rebuild from PostgreSQL on next query."""
        with self._lock:
            self._is_initialized = False

    def rebuild_from_db(self, db: Session) -> int:
        """Load all READY document chunks from PostgreSQL and rebuild the BM25 index from scratch."""
        with self._lock:
            logger.info("Rebuilding BM25 keyword index from PostgreSQL...")
            self.clear()

            # Query all READY documents with their chunks
            db_chunks = (
                db.query(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .options(joinedload(DocumentChunk.document))
                .filter(Document.status == DocumentStatus.READY)
                .all()
            )

            for chunk in db_chunks:
                doc = chunk.document
                if not doc:
                    continue
                cid = str(chunk.id)
                doc_id = str(doc.id)
                tokens = tokenize_text(chunk.content)
                record = BM25ChunkRecord(
                    chunk_id=cid,
                    document_id=doc_id,
                    content=chunk.content,
                    tokens=tokens,
                    department=doc.department,
                    document_type=doc.document_type,
                    access_level=doc.access_level,
                    page_number=chunk.page_number,
                    end_page=chunk.end_page,
                    section=chunk.section,
                    filename=doc.filename,
                )
                self._chunks[cid] = record
                self._doc_to_chunks[doc_id].add(cid)

            self._rebuild_model_locked()
            self._is_initialized = True
            total_indexed = len(self._chunks)
            logger.info(f"BM25 index successfully rebuilt with {total_indexed} chunks.")
            return total_indexed

    def ensure_initialized(self, db: Session) -> None:
        """Ensure the BM25 index has been populated from PostgreSQL before querying."""
        if not self._is_initialized:
            with self._lock:
                if not self._is_initialized:
                    self.rebuild_from_db(db)

    def index_document_chunks(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
        document: Document,
    ) -> None:
        """Dynamically add or replace document chunks in the active BM25 index."""
        with self._lock:
            doc_id_str = str(document_id)
            # Remove any existing chunks for this document to prevent duplicate or stale entries
            old_chunk_ids = self._doc_to_chunks.pop(doc_id_str, set())
            for old_cid in old_chunk_ids:
                self._chunks.pop(old_cid, None)

            # Insert new chunk records
            for chunk in chunks:
                cid = str(chunk.id)
                tokens = tokenize_text(chunk.content)
                record = BM25ChunkRecord(
                    chunk_id=cid,
                    document_id=doc_id_str,
                    content=chunk.content,
                    tokens=tokens,
                    department=document.department,
                    document_type=document.document_type,
                    access_level=document.access_level,
                    page_number=chunk.page_number,
                    end_page=chunk.end_page,
                    section=chunk.section,
                    filename=document.filename,
                )
                self._chunks[cid] = record
                self._doc_to_chunks[doc_id_str].add(cid)

            self._rebuild_model_locked()
            self._is_initialized = True
            logger.info(f"BM25 index updated for document {doc_id_str} with {len(chunks)} chunks.")

    def remove_document(self, document_id: str) -> None:
        """Remove all chunks associated with a document from the BM25 index."""
        with self._lock:
            doc_id_str = str(document_id)
            chunk_ids = self._doc_to_chunks.pop(doc_id_str, set())
            for cid in chunk_ids:
                self._chunks.pop(cid, None)
            self._rebuild_model_locked()
            logger.info(f"BM25 index removed document {doc_id_str} ({len(chunk_ids)} chunks).")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[SearchFilters] = None,
    ) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search over indexed chunks with metadata filtering.
        
        Args:
            query: Raw query text.
            top_k: Maximum candidate matches to return.
            filters: Optional metadata filters.
            
        Returns:
            List of candidate dictionaries: [{"point_id": str, "score": float, "payload": dict}]
        """
        with self._lock:
            if not self._bm25 or not self._ordered_chunk_ids:
                return []

            query_tokens = tokenize_text(query)
            if not query_tokens:
                return []

            raw_scores = self._bm25.get_scores(query_tokens)

            # Match and filter candidate records
            candidates: List[Dict[str, Any]] = []
            for idx, cid in enumerate(self._ordered_chunk_ids):
                score = float(raw_scores[idx])
                if score <= 0.0:
                    continue

                record = self._chunks[cid]

                # Apply metadata filters if provided
                if filters:
                    if filters.department and record.department != filters.department:
                        continue
                    if filters.document_type and record.document_type != filters.document_type:
                        continue
                    if filters.access_level and record.access_level != filters.access_level:
                        continue
                    if filters.document_id and record.document_id != filters.document_id:
                        continue

                payload = {
                    "document_id": record.document_id,
                    "chunk_id": record.chunk_id,
                    "page_number": record.page_number,
                    "end_page": record.end_page,
                    "section": record.section,
                    "department": record.department,
                    "document_type": record.document_type,
                    "access_level": record.access_level,
                    "filename": record.filename,
                }

                candidates.append({
                    "point_id": cid,
                    "score": score,
                    "payload": payload,
                })

            # Sort descending by BM25 score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            return candidates[:top_k]


bm25_index = BM25Index()
