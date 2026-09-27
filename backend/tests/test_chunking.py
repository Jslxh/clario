import uuid
import pytest
from sqlalchemy.orm import Session

from app.schemas.parser import ParsedDocument, ParsedPage
from app.services.chunking.recursive_chunker import RecursiveStructureChunker
from app.services.chunking.service import chunking_service
from app.services.chunking.token_counter import token_counter
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk


def test_1_short_document_remains_single_chunk():
    """1. Verify a short document under target size remains a single chunk."""
    chunker = RecursiveStructureChunker(chunk_size=500, chunk_overlap=75)
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="short_policy.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Employees are entitled to 18 days of annual leave annually.", sections=["Leave Policy"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].section == "Leave Policy"
    assert "Annual Leave" in chunks[0].content or "annual leave" in chunks[0].content


def test_2_3_long_section_split_and_target_size_respected():
    """2 & 3. Verify long section is split into multiple chunks respecting target size."""
    chunker = RecursiveStructureChunker(chunk_size=100, chunk_overlap=15) # ~400 chars max
    long_text = "Paragraph unit sentence detailing enterprise knowledge architecture. " * 30
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="long_architecture.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=long_text, sections=["Architecture"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert len(c.content) <= 600  # Within target character threshold


def test_4_5_overlap_and_section_isolation():
    """4 & 5. Verify overlap exists between adjacent split chunks in continuous section."""
    chunker = RecursiveStructureChunker(chunk_size=25, chunk_overlap=8)
    long_text = "Sentence one about retrieval pipeline. Sentence two about vector embeddings. Sentence three about index search. Sentence four about database models. Sentence five about architecture."
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="pipeline.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=long_text, sections=["Pipeline"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2
    # Check overlap: tail of chunk 0 should overlap with head of chunk 1
    words_c0 = set(chunks[0].content.split())
    words_c1 = set(chunks[1].content.split())
    common = words_c0.intersection(words_c1)
    assert len(common) > 0


def test_6_7_heading_preservation_and_metadata():
    """6 & 7. Verify headings are preserved as context and stored in metadata."""
    chunker = RecursiveStructureChunker(chunk_size=500, chunk_overlap=75)
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="policy.docx",
        document_type="docx",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Requests must be submitted 3 days prior.", sections=["Annual Leave Policy"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Annual Leave Policy"
    assert "# Annual Leave Policy" in chunks[0].content


def test_8_9_page_lineage_single_and_cross_page():
    """8 & 9. Verify page metadata for single and cross-page content."""
    chunker = RecursiveStructureChunker(chunk_size=500, chunk_overlap=75)
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="multipage.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=2,
        pages=[
            ParsedPage(page_number=1, text="Page 1 introduction text.", sections=[]),
            ParsedPage(page_number=2, text="Page 2 continued details text.", sections=[]),
        ],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].start_page == 1
    assert chunks[0].end_page == 2


def test_10_11_12_empty_pages_and_sections_produce_no_empty_chunks():
    """10, 11, 12. Verify empty pages/sections produce 0 empty chunks."""
    chunker = RecursiveStructureChunker()
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="empty.pdf",
        document_type="pdf",
        has_usable_text=False,
        total_pages=2,
        pages=[
            ParsedPage(page_number=1, text="", sections=[]),
            ParsedPage(page_number=2, text="   ", sections=[]),
        ],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 0


def test_13_no_words_cut_in_middle():
    """13. Verify word boundary splitting without cutting words."""
    chunker = RecursiveStructureChunker(chunk_size=20, chunk_overlap=5) # Small target
    text = "Enterprise knowledge management platform architecture"
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="sample.txt",
        document_type="txt",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=text, sections=[])],
    )
    chunks = chunker.chunk_document(doc)
    full_reconstructed = " ".join([c.content for c in chunks])
    for word in ["Enterprise", "knowledge", "management", "platform", "architecture"]:
        assert word in full_reconstructed


def test_14_15_determinism_and_reproducibility():
    """14 & 15. Verify deterministic ordering and chunk content across repeated runs."""
    chunker = RecursiveStructureChunker(chunk_size=100, chunk_overlap=20)
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="determinism.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Deterministic content chunking test. " * 15, sections=["Section A"])],
    )
    run1 = chunker.chunk_document(doc)
    run2 = chunker.chunk_document(doc)
    
    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.chunk_index == c2.chunk_index
        assert c1.content == c2.content
        assert c1.section == c2.section


def test_16_unicode_text_chunking():
    """16. Verify Unicode characters (accents, Japanese, emojis) are preserved."""
    chunker = RecursiveStructureChunker()
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="unicode.txt",
        document_type="txt",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Clario Platform — 日本語テキスト • Café, Naïve & €1000 — 🚀", sections=[])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert "日本語テキスト" in chunks[0].content
    assert "Café, Naïve & €1000" in chunks[0].content


def test_17_txt_documents_no_invented_pages():
    """17. Verify TXT documents do not receive invented page numbers."""
    chunker = RecursiveStructureChunker()
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="plain.txt",
        document_type="txt",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Plain text document without page boundaries.", sections=[])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].start_page is None
    assert chunks[0].end_page is None


def test_18_table_coherence_preservation():
    """18. Verify small table markdown strings remain coherent within single chunk."""
    chunker = RecursiveStructureChunker(chunk_size=500, chunk_overlap=75)
    table_text = "| Department | Access Level |\n| Engineering | Internal |\n| Finance | Confidential |"
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="table.docx",
        document_type="docx",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=table_text, sections=["Data Matrix"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert "| Department | Access Level |" in chunks[0].content


def test_19_oversized_content_recursive_splitting():
    """19. Verify oversized content (10,000+ characters) splits recursively."""
    chunker = RecursiveStructureChunker(chunk_size=200, chunk_overlap=30)
    huge_text = "Enterprise data architecture section paragraph text. " * 200
    doc = ParsedDocument(
        document_id=str(uuid.uuid4()),
        filename="huge.pdf",
        document_type="pdf",
        has_usable_text=True,
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=huge_text, sections=["Big Section"])],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 5


def test_20_reprocessing_prevents_duplicate_persistent_chunks():
    """20. Verify reprocessing a document replaces old chunks without creating duplicate records."""
    doc_uuid = uuid.uuid4()
    doc_id_str = str(doc_uuid)

    with SessionLocal() as db:
        # Create parent document record
        doc_record = Document(
            id=doc_uuid,
            filename="reprocess.pdf",
            title="Reprocess Test Document",
            document_type="pdf",
            access_level="internal",
            file_path="storage/documents/reprocess.pdf",
            file_size=1024,
            status=DocumentStatus.UPLOADED,
        )
        db.add(doc_record)
        db.commit()

        parsed = ParsedDocument(
            document_id=doc_id_str,
            filename="reprocess.pdf",
            document_type="pdf",
            has_usable_text=True,
            total_pages=1,
            pages=[ParsedPage(page_number=1, text="Initial version chunk content.", sections=["V1"])],
        )

        # 1st Processing
        chunks_v1 = chunking_service.chunk_document(parsed)
        db_chunks_v1 = chunking_service.persist_chunks(db, doc_id_str, chunks_v1)
        assert len(db_chunks_v1) == 1

        # 2nd Processing (Reprocessing)
        parsed_v2 = ParsedDocument(
            document_id=doc_id_str,
            filename="reprocess.pdf",
            document_type="pdf",
            has_usable_text=True,
            total_pages=1,
            pages=[
                ParsedPage(page_number=1, text="Updated page 1 content for reprocessing test.", sections=["V2"]),
                ParsedPage(page_number=2, text="Updated page 2 content for reprocessing test.", sections=["V2"]),
            ],
        )
        chunks_v2 = chunking_service.chunk_document(parsed_v2)
        db_chunks_v2 = chunking_service.persist_chunks(db, doc_id_str, chunks_v2)

        # Query total stored chunks for this document
        stored = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).all()
        assert len(stored) == len(db_chunks_v2)
        assert stored[0].section == "V2"

        # Cleanup test document and chunks
        db.delete(doc_record)
        db.commit()
