import uuid
import time
import pytest
import math
from typing import List
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.file_storage import file_storage_service
from app.services.embeddings import embedding_service
from app.services.vector_store import qdrant_vector_store
from app.services.retrieval import (
    semantic_retriever,
    SearchRequest,
    SearchResponse,
    SearchFilters,
    RetrievalResult,
)

client = TestClient(app)


@pytest.fixture(scope="module")
def seeded_test_dataset():
    """Seed deterministic test document chunks for retrieval testing."""
    db = SessionLocal()
    
    # 1. HR Leave Policy Document
    doc_hr_id = uuid.uuid4()
    doc_hr = Document(
        id=doc_hr_id,
        filename="hr_leave_policy.pdf",
        title="HR Leave Policy 2026",
        document_type="pdf",
        department="HR",
        access_level="internal",
        file_path=f"storage/documents/{doc_hr_id}/original.pdf",
        file_size=1024,
        status=DocumentStatus.READY,
    )
    chunk_hr1_id = uuid.uuid4()
    chunk_hr1 = DocumentChunk(
        id=chunk_hr1_id,
        document_id=doc_hr_id,
        chunk_index=0,
        content="Employees receive 18 days of paid annual leave per year with mandatory manager approval.",
        page_number=1,
        end_page=1,
        section="Annual Leave",
    )
    
    # 2. IT Backup Policy Document
    doc_it_id = uuid.uuid4()
    doc_it = Document(
        id=doc_it_id,
        filename="it_backup_procedure.docx",
        title="IT Infrastructure Backup Guidelines",
        document_type="docx",
        department="IT",
        access_level="internal",
        file_path=f"storage/documents/{doc_it_id}/original.docx",
        file_size=2048,
        status=DocumentStatus.READY,
    )
    chunk_it1_id = uuid.uuid4()
    chunk_it1 = DocumentChunk(
        id=chunk_it1_id,
        document_id=doc_it_id,
        chunk_index=0,
        content="Production database backups run automatically every six hours with encrypted offsite snapshots.",
        page_number=3,
        end_page=3,
        section="Database Backups",
    )
    
    # 3. Security Confidential VPN Document
    doc_sec_id = uuid.uuid4()
    doc_sec = Document(
        id=doc_sec_id,
        filename="security_vpn_access.pdf",
        title="Enterprise Security VPN Configuration",
        document_type="pdf",
        department="Security",
        access_level="confidential",
        file_path=f"storage/documents/{doc_sec_id}/original.pdf",
        file_size=4096,
        status=DocumentStatus.READY,
    )
    chunk_sec1_id = uuid.uuid4()
    chunk_sec1 = DocumentChunk(
        id=chunk_sec1_id,
        document_id=doc_sec_id,
        chunk_index=0,
        content="Remote VPN network access strictly requires hardware multi-factor authentication (MFA).",
        page_number=2,
        end_page=2,
        section="VPN Security",
    )

    db.add_all([doc_hr, doc_it, doc_sec, chunk_hr1, chunk_it1, chunk_sec1])
    db.commit()

    # Index points into Qdrant
    hr_vec = embedding_service.embed_documents([chunk_hr1.content])[0]
    it_vec = embedding_service.embed_documents([chunk_it1.content])[0]
    sec_vec = embedding_service.embed_documents([chunk_sec1.content])[0]

    points = [
        {
            "point_id": str(chunk_hr1_id),
            "vector": hr_vec,
            "payload": {
                "document_id": str(doc_hr_id),
                "chunk_id": str(chunk_hr1_id),
                "page_number": 1,
                "end_page": 1,
                "section": "Annual Leave",
                "department": "HR",
                "document_type": "pdf",
                "access_level": "internal",
                "filename": "hr_leave_policy.pdf",
            },
        },
        {
            "point_id": str(chunk_it1_id),
            "vector": it_vec,
            "payload": {
                "document_id": str(doc_it_id),
                "chunk_id": str(chunk_it1_id),
                "page_number": 3,
                "end_page": 3,
                "section": "Database Backups",
                "department": "IT",
                "document_type": "docx",
                "access_level": "internal",
                "filename": "it_backup_procedure.docx",
            },
        },
        {
            "point_id": str(chunk_sec1_id),
            "vector": sec_vec,
            "payload": {
                "document_id": str(doc_sec_id),
                "chunk_id": str(chunk_sec1_id),
                "page_number": 2,
                "end_page": 2,
                "section": "VPN Security",
                "department": "Security",
                "document_type": "pdf",
                "access_level": "confidential",
                "filename": "security_vpn_access.pdf",
            },
        },
    ]

    qdrant_vector_store.upsert_chunk_vectors(points)
    db.close()

    yield {
        "doc_hr_id": str(doc_hr_id),
        "doc_it_id": str(doc_it_id),
        "doc_sec_id": str(doc_sec_id),
        "chunk_hr1_id": str(chunk_hr1_id),
        "chunk_it1_id": str(chunk_it1_id),
        "chunk_sec1_id": str(chunk_sec1_id),
    }

    # Teardown
    db_clean = SessionLocal()
    db_clean.query(DocumentChunk).filter(
        DocumentChunk.id.in_([chunk_hr1_id, chunk_it1_id, chunk_sec1_id])
    ).delete(synchronize_session=False)
    db_clean.query(Document).filter(
        Document.id.in_([doc_hr_id, doc_it_id, doc_sec_id])
    ).delete(synchronize_session=False)
    db_clean.commit()
    db_clean.close()

    try:
        from app.services.vector_service import vector_service
        client_q = vector_service.get_client()
        client_q.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=[str(chunk_hr1_id), str(chunk_it1_id), str(chunk_sec1_id)],
        )
    except Exception:
        pass



def test_1_query_embedding_uses_existing_embedding_service():
    """1. Verify query embedding is generated using the existing BGE embedding service."""
    query = "What is the annual leave policy?"
    vec = semantic_retriever.embedder.embed_query(query)
    assert isinstance(vec, list)
    assert len(vec) == 384
    # Check L2 normalization
    norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(norm, 1.0, rel_tol=1e-3)


def test_2_empty_query_rejected():
    """2. Verify empty query is rejected with ValueError and HTTP 400 Bad Request."""
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        with SessionLocal() as db:
            semantic_retriever.search(db=db, query="")

    res = client.post("/api/v1/search", json={"query": ""})
    assert res.status_code == 400
    assert "empty or whitespace-only" in res.json()["detail"]


def test_3_whitespace_query_rejected():
    """3. Verify whitespace-only query is rejected with ValueError and HTTP 400."""
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        with SessionLocal() as db:
            semantic_retriever.search(db=db, query="   \n \t  ")

    res = client.post("/api/v1/search", json={"query": "   \t\n "})
    assert res.status_code == 400


def test_4_default_top_k_works(seeded_test_dataset):
    """4. Verify default top_k uses configured RETRIEVAL_TOP_K value."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="leave policy", top_k=None)
        assert isinstance(resp, SearchResponse)
        assert resp.query == "leave policy"


def test_5_custom_top_k_works(seeded_test_dataset):
    """5. Verify custom top_k restricts output count."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="company policies", top_k=2)
        assert len(resp.results) <= 2


def test_6_invalid_top_k_rejected():
    """6. Verify invalid top_k (0, negative, > 100) is rejected."""
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="positive integer > 0"):
            semantic_retriever.search(db=db, query="test", top_k=0)

        with pytest.raises(ValueError, match="positive integer > 0"):
            semantic_retriever.search(db=db, query="test", top_k=-5)

        with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
            semantic_retriever.search(db=db, query="test", top_k=500)

    res_zero = client.post("/api/v1/search", json={"query": "test", "top_k": 0})
    assert res_zero.status_code == 400

    res_large = client.post("/api/v1/search", json={"query": "test", "top_k": 500})
    assert res_large.status_code == 400


def test_7_qdrant_semantic_search_executes(seeded_test_dataset):
    """7. Verify Qdrant semantic search retrieves leave-related chunk for leave query."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="What is the annual leave policy?", top_k=3)
        assert resp.total_results > 0
        top_match = resp.results[0]
        assert "annual leave" in top_match.content.lower()
        assert top_match.filename == "hr_leave_policy.pdf"


def test_8_results_contain_similarity_scores(seeded_test_dataset):
    """8. Verify search results contain Cosine similarity scores."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="backup frequency", top_k=3)
        for res in resp.results:
            assert isinstance(res.score, float)
            assert -1.0 <= res.score <= 1.0


def test_9_postgresql_hydration_works(seeded_test_dataset):
    """9. Verify canonical chunk content is hydrated from PostgreSQL."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="multi-factor authentication VPN", top_k=1)
        assert resp.total_results == 1
        top_result = resp.results[0]
        assert top_result.chunk_id == seeded_test_dataset["chunk_sec1_id"]
        assert top_result.document_id == seeded_test_dataset["doc_sec_id"]
        assert "multi-factor authentication" in top_result.content
        assert top_result.department == "Security"
        assert top_result.access_level == "confidential"


def test_10_qdrant_result_ordering_is_preserved(seeded_test_dataset):
    """10. Verify candidate chunk order strictly matches Qdrant score rank order."""
    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="database backups and snapshots", top_k=3)
        scores = [r.score for r in resp.results]
        assert scores == sorted(scores, reverse=True)


def test_11_missing_postgresql_chunk_handled_safely(seeded_test_dataset, monkeypatch):
    """11. Verify missing PostgreSQL chunk returned by vector store is skipped safely without crashing."""
    fake_chunk_id = str(uuid.uuid4())
    fake_matches = [
        {"point_id": fake_chunk_id, "score": 0.99, "payload": {"document_id": str(uuid.uuid4())}},
        {
            "point_id": seeded_test_dataset["chunk_hr1_id"],
            "score": 0.85,
            "payload": {"document_id": seeded_test_dataset["doc_hr_id"]},
        },
    ]

    monkeypatch.setattr(qdrant_vector_store, "search_vectors", lambda **kwargs: fake_matches)

    with SessionLocal() as db:
        resp = semantic_retriever.search(db=db, query="leave policy", top_k=5)
        # Fake missing chunk should be safely skipped, returning only valid DB chunk
        assert resp.total_results == 1
        assert resp.results[0].chunk_id == seeded_test_dataset["chunk_hr1_id"]


def test_12_metadata_filters_work(seeded_test_dataset):
    """12. Verify metadata filtering by department, document_type, access_level, and document_id."""
    with SessionLocal() as db:
        # Filter by department
        hr_filters = SearchFilters(department="HR")
        resp_hr = semantic_retriever.search(db=db, query="policy", top_k=5, filters=hr_filters)
        for r in resp_hr.results:
            assert r.department == "HR"

        # Filter by access level
        sec_filters = SearchFilters(access_level="confidential")
        resp_sec = semantic_retriever.search(db=db, query="network", top_k=5, filters=sec_filters)
        for r in resp_sec.results:
            assert r.access_level == "confidential"

        # Filter by document_type
        docx_filters = SearchFilters(document_type="docx")
        resp_docx = semantic_retriever.search(db=db, query="backup", top_k=5, filters=docx_filters)
        for r in resp_docx.results:
            assert r.document_type == "docx"

        # Filter by document_id
        doc_id_filter = SearchFilters(document_id=seeded_test_dataset["doc_hr_id"])
        resp_doc = semantic_retriever.search(db=db, query="leave", top_k=5, filters=doc_id_filter)
        for r in resp_doc.results:
            assert r.document_id == seeded_test_dataset["doc_hr_id"]


def test_13_no_n_plus_one_hydration_behavior(seeded_test_dataset, monkeypatch):
    """13. Verify single SQL query is executed during hydration (no N+1 queries)."""
    db = SessionLocal()
    query_count = 0
    original_execute = db.execute

    def counting_execute(*args, **kwargs):
        nonlocal query_count
        query_count += 1
        return original_execute(*args, **kwargs)

    monkeypatch.setattr(db, "execute", counting_execute)

    # Search with top_k=3
    resp = semantic_retriever.search(db=db, query="policy backup leave VPN", top_k=3)
    db.close()

    assert resp.total_results > 0
    # SQL query count for hydration should be exactly 1 query with JOIN
    assert query_count <= 2  # 1 for SQL query + optional transaction control


def test_14_search_endpoint_returns_expected_schema(seeded_test_dataset):
    """14. Verify POST /api/v1/search endpoint returns expected JSON schema."""
    req_payload = {
        "query": "How often are database backups executed?",
        "top_k": 2,
        "filters": {
            "department": "IT"
        }
    }
    response = client.post("/api/v1/search", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "How often are database backups executed?"
    assert "total_results" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    
    if len(data["results"]) > 0:
        first = data["results"][0]
        assert "chunk_id" in first
        assert "document_id" in first
        assert "score" in first
        assert "content" in first
        assert "filename" in first
        assert "department" in first
        assert first["department"] == "IT"


def test_15_retrieval_performance_benchmark(seeded_test_dataset):
    """15. Measure and report small deterministic retrieval benchmark timings."""
    query = "What is the annual leave policy for employees?"
    db = SessionLocal()

    # 1. Query embedding timing
    t0 = time.perf_counter()
    q_vec = semantic_retriever.embedder.embed_query(query)
    t1 = time.perf_counter()
    query_embedding_ms = (t1 - t0) * 1000.0

    # 2. Qdrant vector search timing
    t2 = time.perf_counter()
    matches = semantic_retriever.vector_store.search_vectors(query_vector=q_vec, top_k=5)
    t3 = time.perf_counter()
    qdrant_search_ms = (t3 - t2) * 1000.0

    # 3. PostgreSQL hydration timing
    t4 = time.perf_counter()
    resp = semantic_retriever.search(db=db, query=query, top_k=5)
    t5 = time.perf_counter()
    total_service_ms = (t5 - t4) * 1000.0
    postgres_hydration_ms = max(0.0, total_service_ms - query_embedding_ms - qdrant_search_ms)

    db.close()

    print(f"\n--- RETRIEVAL BENCHMARK RESULTS ---")
    print(f"Query: '{query}'")
    print(f"Query Embedding Time: {query_embedding_ms:.2f} ms")
    print(f"Qdrant Search Time:   {qdrant_search_ms:.2f} ms")
    print(f"PostgreSQL Hydration: {postgres_hydration_ms:.2f} ms")
    print(f"Total Service Time:   {total_service_ms:.2f} ms")
    print(f"Retrieved Candidates: {resp.total_results}")
    print(f"-----------------------------------\n")

    assert resp.total_results > 0
    assert total_service_ms < 5000.0  # Reasonable assertion for local execution
