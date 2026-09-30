import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import embedding_service
from app.services.vector_store import qdrant_vector_store
from app.services.retrieval import (
    bm25_index,
    hybrid_retriever,
    RetrievalMode,
)
from app.services.generation import generation_service, GenerationService
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import ContextLengthExceededError

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixture: Seed deterministic 4-chunk multi-topic dataset
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generation_dataset():
    """Seed multi-topic document chunks in PostgreSQL, Qdrant, and BM25 index."""
    try:
        from app.services.vector_service import vector_service
        vector_service.get_client().delete_collection(settings.QDRANT_COLLECTION_NAME)
        vector_service.ensure_collection_exists()
    except Exception:
        pass

    db = SessionLocal()

    # 1. HR Annual Vacation Policy
    doc_hr_id = uuid.UUID("a1111111-1111-1111-1111-111111111111")
    doc_hr = Document(
        id=doc_hr_id,
        filename="hr_leave_policy.pdf",
        title="Annual Leave and Vacation Policy 2026",
        document_type="pdf",
        department="HR",
        access_level="internal",
        file_path=f"storage/documents/{doc_hr_id}/original.pdf",
        file_size=1024,
        status=DocumentStatus.READY,
    )
    chunk_hr_id = uuid.UUID("a1111111-1111-1111-1111-111111111112")
    chunk_hr = DocumentChunk(
        id=chunk_hr_id,
        document_id=doc_hr_id,
        chunk_index=0,
        content="Policy code POL-HR-2026-A: All full-time employees receive 18 days of paid annual vacation leave.",
        page_number=1,
        end_page=1,
        section="Annual Leave Policy",
    )

    # 2. IT Database Operations
    doc_it_id = uuid.UUID("a2222222-2222-2222-2222-222222222221")
    doc_it = Document(
        id=doc_it_id,
        filename="it_database_operations.docx",
        title="Database Operations and Error Codes",
        document_type="docx",
        department="IT",
        access_level="internal",
        file_path=f"storage/documents/{doc_it_id}/original.docx",
        file_size=2048,
        status=DocumentStatus.READY,
    )
    chunk_it_id = uuid.UUID("a2222222-2222-2222-2222-222222222222")
    chunk_it = DocumentChunk(
        id=chunk_it_id,
        document_id=doc_it_id,
        chunk_index=0,
        content="Error code ERR-DB-504 occurs when write replication fails on standby nodes during automated backups.",
        page_number=4,
        end_page=4,
        section="Troubleshooting Errors",
    )

    # 3. Security MFA & Authentication
    doc_sec_id = uuid.UUID("a3333333-3333-3333-3333-333333333331")
    doc_sec = Document(
        id=doc_sec_id,
        filename="security_compliance.pdf",
        title="Security Compliance and Network Access",
        document_type="pdf",
        department="Security",
        access_level="confidential",
        file_path=f"storage/documents/{doc_sec_id}/original.pdf",
        file_size=4096,
        status=DocumentStatus.READY,
    )
    chunk_sec_id = uuid.UUID("a3333333-3333-3333-3333-333333333332")
    chunk_sec = DocumentChunk(
        id=chunk_sec_id,
        document_id=doc_sec_id,
        chunk_index=0,
        content="Standard SEC-MFA-992: Production VPN access strictly requires physical FIDO2 YubiKey authentication tokens.",
        page_number=2,
        end_page=2,
        section="Network Security",
    )

    all_docs = [doc_hr, doc_it, doc_sec]
    all_chunks = [chunk_hr, chunk_it, chunk_sec]

    db.add_all(all_docs + all_chunks)
    db.commit()

    # Index in Qdrant
    embeddings = embedding_service.embed_documents([c.content for c in all_chunks])
    qdrant_points = []
    for c, doc, vec in zip(all_chunks, all_docs, embeddings):
        qdrant_points.append({
            "point_id": str(c.id),
            "vector": vec,
            "payload": {
                "document_id": str(doc.id),
                "chunk_id": str(c.id),
                "page_number": c.page_number,
                "end_page": c.end_page,
                "section": c.section,
                "department": doc.department,
                "document_type": doc.document_type,
                "access_level": doc.access_level,
                "filename": doc.filename,
            },
        })
    qdrant_vector_store.upsert_chunk_vectors(qdrant_points)

    # Rebuild BM25 index
    bm25_index.rebuild_from_db(db)
    db.close()

    dataset_info = {
        "chunk_hr_id": str(chunk_hr_id),
        "chunk_it_id": str(chunk_it_id),
        "chunk_sec_id": str(chunk_sec_id),
    }

    yield dataset_info

    # Teardown
    db_clean = SessionLocal()
    chunk_ids = [c.id for c in all_chunks]
    doc_ids = [d.id for d in all_docs]
    db_clean.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).delete(synchronize_session=False)
    db_clean.query(Document).filter(Document.id.in_(doc_ids)).delete(synchronize_session=False)
    db_clean.commit()
    db_clean.close()

    try:
        from app.services.vector_service import vector_service
        from qdrant_client.models import PointIdsList
        vector_service.get_client().delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=PointIdsList(points=[str(cid) for cid in chunk_ids]),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Integration Tests for POST /api/v1/query
# ---------------------------------------------------------------------------

def test_1_query_endpoint_valid_qna_with_citations(generation_dataset):
    """1. Test POST /api/v1/query returns synthesized answer with valid mapped citations."""
    req_body = {
        "query": "How many days of paid vacation do employees receive?",
        "top_k": 3,
        "mode": "hybrid",
    }
    resp = client.post("/api/v1/query", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_sufficient_context"] is True
    assert "18 days" in data["answer"]
    assert "[Doc-1]" in data["answer"]
    assert len(data["citations"]) > 0

    first_citation = data["citations"][0]
    assert first_citation["source_tag"] == "[Doc-1]"
    assert first_citation["filename"] == "hr_leave_policy.pdf"
    assert first_citation["chunk_id"] == generation_dataset["chunk_hr_id"]
    assert data["token_usage"]["total_tokens"] > 0
    assert data["latency_ms"] > 0


def test_2_query_endpoint_unknown_citation_tags_stripped(generation_dataset):
    """2. Test that hallucinated/unknown citation tags like [Doc-99] are stripped from answer and omitted from citations."""
    mock_provider = MockLLMProvider(simulate_unknown_tag=True)
    custom_gen_service = GenerationService(provider=mock_provider)

    with SessionLocal() as db:
        resp = custom_gen_service.answer_query(
            db=db,
            query="ERR-DB-504 database error",
            top_k=2,
        )

    # [Doc-99] should be stripped from answer and not present in citations list
    assert "[Doc-99]" not in resp.answer
    assert all(c.source_tag != "[Doc-99]" for c in resp.citations)


def test_3_query_endpoint_zero_match_abstention(generation_dataset):
    """3. Test zero-match query returns has_sufficient_context=False and abstention text."""
    req_body = {
        "query": "quantum gravity black hole singularity thermodynamics",
        "top_k": 3,
        "filters": {"department": "NonExistentDept"},
    }
    resp = client.post("/api/v1/query", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_sufficient_context"] is False
    assert "could not find sufficient information" in data["answer"].lower()
    assert len(data["citations"]) == 0
    assert data["token_usage"]["prompt_tokens"] == 0


def test_4_query_endpoint_department_metadata_filtering(generation_dataset):
    """4. Test department metadata filter restricts retrieval and answer synthesis context."""
    req_body = {
        "query": "VPN access security requirements",
        "top_k": 3,
        "filters": {"department": "Security"},
    }
    resp = client.post("/api/v1/query", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_sufficient_context"] is True
    assert "FIDO2" in data["answer"]
    for cit in data["citations"]:
        assert cit["department"] == "Security"


def test_5_context_length_exceeded_deterministic_recovery(generation_dataset):
    """5. Test that when provider raises ContextLengthExceededError, GenerationService rebuilds with reduced chunks."""
    call_count = 0

    def mock_generate(req):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ContextLengthExceededError("Context window exceeded")
        return MockLLMProvider().generate(req)

    mock_provider = MockLLMProvider()
    with patch.object(mock_provider, "generate", side_effect=mock_generate):
        custom_service = GenerationService(provider=mock_provider)
        with SessionLocal() as db:
            resp = custom_service.answer_query(
                db=db,
                query="annual vacation leave",
                top_k=3,
            )

        assert call_count == 2  # Verified retry with reduced chunks occurred
        assert resp.has_sufficient_context is True
        assert len(resp.citations) > 0


def test_6_empty_query_validation():
    """6. Verify empty query is rejected with 400 Bad Request."""
    resp = client.post("/api/v1/query", json={"query": "   ", "top_k": 3})
    assert resp.status_code == 400


def test_7_search_endpoint_backward_compatibility():
    """7. Verify POST /api/v1/search contract remains fully intact and functioning."""
    resp = client.post("/api/v1/search", json={"query": "POL-HR-2026-A", "top_k": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0
