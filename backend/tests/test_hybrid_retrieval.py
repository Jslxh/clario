import uuid
import math
import pytest
from unittest.mock import patch
from typing import List, Set, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.document_service import document_service
from app.services.embeddings import embedding_service
from app.services.vector_store import qdrant_vector_store
from app.services.retrieval import (
    RetrievalMode,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    tokenize_text,
    bm25_index,
    BM25Index,
    reciprocal_rank_fusion,
    hybrid_retriever,
    semantic_retriever,
    compute_retrieval_metrics,
    compute_macro_retrieval_metrics,
    EvaluationMetrics,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixture: Seed deterministic 8-chunk dataset with distinct semantic & keyword topics
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def hybrid_dataset():
    """Seed multi-topic document chunks in PostgreSQL, Qdrant, and BM25 index."""
    try:
        from app.services.vector_service import vector_service
        vector_service.get_client().delete_collection(settings.QDRANT_COLLECTION_NAME)
        vector_service.ensure_collection_exists()
    except Exception:
        pass

    db = SessionLocal()

    # 1. HR Annual Leave Policy (Policy code: POL-HR-2026-A)
    doc_hr_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
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
    chunk_hr_id = uuid.UUID("11111111-1111-1111-1111-111111111112")
    chunk_hr = DocumentChunk(
        id=chunk_hr_id,
        document_id=doc_hr_id,
        chunk_index=0,
        content="Policy code POL-HR-2026-A: All full-time employees receive 18 days of paid annual vacation leave.",
        page_number=1,
        end_page=1,
        section="Annual Leave Policy",
    )

    # 2. Database Error Codes & Backup (Technical code: ERR-DB-504)
    doc_it_id = uuid.UUID("22222222-2222-2222-2222-222222222221")
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
    chunk_it_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    chunk_it = DocumentChunk(
        id=chunk_it_id,
        document_id=doc_it_id,
        chunk_index=0,
        content="Error code ERR-DB-504 occurs when write replication fails on standby nodes during automated midnight backups.",
        page_number=4,
        end_page=4,
        section="Troubleshooting Errors",
    )

    # 3. Security MFA & VPN (Standard code: SEC-MFA-992)
    doc_sec_id = uuid.UUID("33333333-3333-3333-3333-333333333331")
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
    chunk_sec_id = uuid.UUID("33333333-3333-3333-3333-333333333332")
    chunk_sec = DocumentChunk(
        id=chunk_sec_id,
        document_id=doc_sec_id,
        chunk_index=0,
        content="Standard SEC-MFA-992: Production VPN access strictly requires physical FIDO2 YubiKey authentication tokens.",
        page_number=2,
        end_page=2,
        section="Network Security",
    )

    # 4. HR Sick Leave & Medical Incapacitation (Synonym mismatch target)
    doc_hr_sick_id = uuid.UUID("44444444-4444-4444-4444-444444444441")
    doc_hr_sick = Document(
        id=doc_hr_sick_id,
        filename="hr_medical_allowance.pdf",
        title="Medical Incapacitation and Health Recovery Compensation",
        document_type="pdf",
        department="HR",
        access_level="internal",
        file_path=f"storage/documents/{doc_hr_sick_id}/original.pdf",
        file_size=1536,
        status=DocumentStatus.READY,
    )
    chunk_hr_sick_id = uuid.UUID("44444444-4444-4444-4444-444444444442")
    chunk_hr_sick = DocumentChunk(
        id=chunk_hr_sick_id,
        document_id=doc_hr_sick_id,
        chunk_index=0,
        content="Policy clause POL-HR-2026-B: Sickness allowance and illness incapacitation recovery stipend provides 10 statutory wellness days per calendar year for medical treatment.",
        page_number=1,
        end_page=1,
        section="Medical Incapacitation Policy",
    )

    # 5. IT Networking Distractor (Overlaps 'standby', 'errors', 'routing')
    doc_it_net_id = uuid.UUID("55555555-5555-5555-5555-555555555551")
    doc_it_net = Document(
        id=doc_it_net_id,
        filename="it_network_routing.docx",
        title="Network Operations and Subnet Routing",
        document_type="docx",
        department="IT",
        access_level="internal",
        file_path=f"storage/documents/{doc_it_net_id}/original.docx",
        file_size=1800,
        status=DocumentStatus.READY,
    )
    chunk_it_net_id = uuid.UUID("55555555-5555-5555-5555-555555555552")
    chunk_it_net = DocumentChunk(
        id=chunk_it_net_id,
        document_id=doc_it_net_id,
        chunk_index=0,
        content="Diagnostic guide NET-ROUTE-101: Standby failover routing occurs over BGP mesh during network partition errors.",
        page_number=2,
        end_page=2,
        section="Network Routing Operations",
    )

    # 6. Security VPN Passwords & Credentials (Multi-relevant target with chunk_sec)
    doc_sec_pw_id = uuid.UUID("66666666-6666-6666-6666-666666666661")
    doc_sec_pw = Document(
        id=doc_sec_pw_id,
        filename="security_identity_passwords.pdf",
        title="Identity and Access Control Guidelines",
        document_type="pdf",
        department="Security",
        access_level="confidential",
        file_path=f"storage/documents/{doc_sec_pw_id}/original.pdf",
        file_size=3200,
        status=DocumentStatus.READY,
    )
    chunk_sec_pw_id = uuid.UUID("66666666-6666-6666-6666-666666666662")
    chunk_sec_pw = DocumentChunk(
        id=chunk_sec_pw_id,
        document_id=doc_sec_pw_id,
        chunk_index=0,
        content="Standard SEC-IAM-404: Remote employee VPN credentials require 16-character alphanumeric passwords changed quarterly alongside digital certificate renewal.",
        page_number=1,
        end_page=1,
        section="Password and Access Policies",
    )

    # 7. Finance Travel Reimbursement Distractor
    doc_fin_id = uuid.UUID("77777777-7777-7777-7777-777777777771")
    doc_fin = Document(
        id=doc_fin_id,
        filename="finance_travel_policy.pdf",
        title="Corporate Travel Reimbursement Policy",
        document_type="pdf",
        department="Finance",
        access_level="internal",
        file_path=f"storage/documents/{doc_fin_id}/original.pdf",
        file_size=2500,
        status=DocumentStatus.READY,
    )
    chunk_fin_id = uuid.UUID("77777777-7777-7777-7777-777777777772")
    chunk_fin = DocumentChunk(
        id=chunk_fin_id,
        document_id=doc_fin_id,
        chunk_index=0,
        content="Policy FIN-TRV-880: Flight reservations and hotel lodging expenses must be submitted through Concur within 30 days of business travel completion.",
        page_number=1,
        end_page=1,
        section="Travel Expenses",
    )

    # 8. IT Database Performance Distractor (Overlaps 'database', 'queries')
    doc_db_perf_id = uuid.UUID("88888888-8888-8888-8888-888888888881")
    doc_db_perf = Document(
        id=doc_db_perf_id,
        filename="it_database_performance.docx",
        title="Database Query Optimization and Connection Pooling",
        document_type="docx",
        department="IT",
        access_level="internal",
        file_path=f"storage/documents/{doc_db_perf_id}/original.docx",
        file_size=2200,
        status=DocumentStatus.READY,
    )
    chunk_db_perf_id = uuid.UUID("88888888-8888-8888-8888-888888888882")
    chunk_db_perf = DocumentChunk(
        id=chunk_db_perf_id,
        document_id=doc_db_perf_id,
        chunk_index=0,
        content="Technical note PERF-DB-300: PostgreSQL connection pool exhaustion causes high query latency during high concurrency transactions.",
        page_number=1,
        end_page=1,
        section="Database Performance",
    )

    all_docs = [doc_hr, doc_it, doc_sec, doc_hr_sick, doc_it_net, doc_sec_pw, doc_fin, doc_db_perf]
    all_chunks = [
        chunk_hr, chunk_it, chunk_sec, chunk_hr_sick,
        chunk_it_net, chunk_sec_pw, chunk_fin, chunk_db_perf,
    ]

    db.add_all(all_docs + all_chunks)
    db.commit()

    # Index all chunks in Qdrant
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

    # Rebuild BM25 index from database
    bm25_index.rebuild_from_db(db)
    db.close()

    dataset_info = {
        "doc_hr_id": str(doc_hr_id),
        "doc_it_id": str(doc_it_id),
        "doc_sec_id": str(doc_sec_id),
        "doc_hr_sick_id": str(doc_hr_sick_id),
        "doc_it_net_id": str(doc_it_net_id),
        "doc_sec_pw_id": str(doc_sec_pw_id),
        "doc_fin_id": str(doc_fin_id),
        "doc_db_perf_id": str(doc_db_perf_id),
        "chunk_hr_id": str(chunk_hr_id),
        "chunk_it_id": str(chunk_it_id),
        "chunk_sec_id": str(chunk_sec_id),
        "chunk_hr_sick_id": str(chunk_hr_sick_id),
        "chunk_it_net_id": str(chunk_it_net_id),
        "chunk_sec_pw_id": str(chunk_sec_pw_id),
        "chunk_fin_id": str(chunk_fin_id),
        "chunk_db_perf_id": str(chunk_db_perf_id),
    }

    yield dataset_info

    # Teardown: Clean DB and Qdrant
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
# Unit & Component Tests: Tokenization, Empty Corpus, RRF Formula, Metric Edge Cases
# ---------------------------------------------------------------------------

def test_1_tokenization_handles_text_and_special_cases():
    """1. Test tokenization on normal words, technical codes, whitespace, and punctuation."""
    tokens1 = tokenize_text("What is the annual vacation leave policy?")
    assert tokens1 == ["what", "is", "the", "annual", "vacation", "leave", "policy"]

    tokens2 = tokenize_text("Encountered error ERR-DB-504 on node_1.")
    assert "err-db-504" in tokens2
    assert "error" in tokens2
    assert "node_1" in tokens2

    assert tokenize_text("") == []
    assert tokenize_text("   \t\n ") == []
    assert tokenize_text("!@#$%^&*()") == []


def test_2_empty_bm25_corpus_handled_safely():
    """2. Test that an uninitialized or empty BM25 index returns empty results without error."""
    fresh_bm25 = BM25Index()
    res = fresh_bm25.search("annual leave", top_k=5)
    assert res == []

    res_empty_query = fresh_bm25.search("", top_k=5)
    assert res_empty_query == []


def test_3_rrf_formula_and_1_based_ranking():
    """3. Verify Reciprocal Rank Fusion mathematical formula: 1 / (k + rank) with 1-based ranks."""
    k = 60
    candidates_semantic = [
        {"point_id": "docA", "score": 0.95},
        {"point_id": "docB", "score": 0.80},
    ]
    candidates_bm25 = [
        {"point_id": "docB", "score": 12.5},
        {"point_id": "docC", "score": 8.0},
    ]

    fused = reciprocal_rank_fusion(
        ranked_lists={"semantic": candidates_semantic, "bm25": candidates_bm25},
        k=k,
    )

    fused_dict = {f.point_id: f for f in fused}
    assert math.isclose(fused_dict["docB"].rrf_score, (1.0 / 62.0) + (1.0 / 61.0), rel_tol=1e-5)
    assert math.isclose(fused_dict["docA"].rrf_score, 1.0 / 61.0, rel_tol=1e-5)
    assert math.isclose(fused_dict["docC"].rrf_score, 1.0 / 62.0, rel_tol=1e-5)

    assert fused[0].point_id == "docB"
    assert fused[1].point_id == "docA"
    assert fused[2].point_id == "docC"


def test_4_rrf_tie_breaking_is_deterministic():
    """4. Verify deterministic tie-breaking when two candidates have identical RRF scores."""
    k = 60
    list_a = [{"point_id": "chunk-222", "score": 0.8}]
    list_b = [{"point_id": "chunk-111", "score": 5.0}]

    fused1 = reciprocal_rank_fusion(
        ranked_lists={"retriever1": list_a, "retriever2": list_b},
        k=k,
    )
    fused2 = reciprocal_rank_fusion(
        ranked_lists={"retriever1": list_a, "retriever2": list_b},
        k=k,
    )

    assert len(fused1) == 2
    assert fused1[0].point_id == "chunk-111"
    assert fused1[1].point_id == "chunk-222"
    assert [f.point_id for f in fused1] == [f.point_id for f in fused2]


def test_4b_retrieval_metrics_unit_edge_cases():
    """4b. Unit test compute_retrieval_metrics on edge cases: empty sets, multiple relevant chunks, zero relevance."""
    # Case 1: Empty relevant chunk set (zero-match queries)
    m_zero = compute_retrieval_metrics(
        retrieved_chunk_ids=["c1", "c2", "c3"],
        relevant_chunk_ids=set(),
        k=3,
    )
    assert m_zero.precision_at_k == 0.0
    assert m_zero.recall_at_k == 0.0
    assert m_zero.mrr == 0.0

    # Case 2: Empty retrieved chunk IDs
    m_empty_ret = compute_retrieval_metrics(
        retrieved_chunk_ids=[],
        relevant_chunk_ids={"c1"},
        k=3,
    )
    assert m_empty_ret.precision_at_k == 0.0
    assert m_empty_ret.recall_at_k == 0.0
    assert m_empty_ret.mrr == 0.0

    # Case 3: Multiple relevant chunks (2 relevant: c1, c2), retrieved [c1, c3, c2], k=3
    # Precision@3 = 2/3 = 0.6667, Recall@3 = 2/2 = 1.0, MRR = 1/1 = 1.0 (c1 at rank 1)
    m_multi = compute_retrieval_metrics(
        retrieved_chunk_ids=["c1", "c3", "c2"],
        relevant_chunk_ids={"c1", "c2"},
        k=3,
    )
    assert m_multi.precision_at_k == 0.6667
    assert m_multi.recall_at_k == 1.0
    assert m_multi.mrr == 1.0

    # Case 4: Multiple relevant chunks, first match at rank 2 [c0, c2, c3] with relevant {c1, c2}
    # Precision@3 = 1/3 = 0.3333, Recall@3 = 1/2 = 0.5, MRR = 1/2 = 0.5
    m_rank2 = compute_retrieval_metrics(
        retrieved_chunk_ids=["c0", "c2", "c3"],
        relevant_chunk_ids={"c1", "c2"},
        k=3,
    )
    assert m_rank2.precision_at_k == 0.3333
    assert m_rank2.recall_at_k == 0.5
    assert m_rank2.mrr == 0.5

    # Case 5: Fewer than K retrieved results (1 retrieved out of k=3)
    # Precision@3 must use k=3 as denominator: 1 / 3 = 0.3333
    m_fewer = compute_retrieval_metrics(
        retrieved_chunk_ids=["c1"],
        relevant_chunk_ids={"c1"},
        k=3,
    )
    assert m_fewer.precision_at_k == 0.3333
    assert m_fewer.recall_at_k == 1.0
    assert m_fewer.mrr == 1.0


# ---------------------------------------------------------------------------
# Integration Tests: BM25 Search, Metadata Filters, Exact Identifier Match
# ---------------------------------------------------------------------------

def test_5_bm25_exact_code_retrieval(hybrid_dataset):
    """5. Verify BM25 directly matches exact technical identifier 'ERR-DB-504'."""
    with SessionLocal() as db:
        resp = hybrid_retriever.search(
            db=db,
            query="ERR-DB-504",
            top_k=3,
            mode=RetrievalMode.BM25,
        )
        assert resp.mode == "bm25"
        assert resp.total_results > 0
        top = resp.results[0]
        assert top.chunk_id == hybrid_dataset["chunk_it_id"]
        assert "ERR-DB-504" in top.content


def test_6_bm25_policy_code_retrieval(hybrid_dataset):
    """6. Verify BM25 directly matches policy code 'POL-HR-2026-A'."""
    with SessionLocal() as db:
        resp = hybrid_retriever.search(
            db=db,
            query="POL-HR-2026-A",
            top_k=3,
            mode=RetrievalMode.BM25,
        )
        assert resp.total_results > 0
        top = resp.results[0]
        assert top.chunk_id == hybrid_dataset["chunk_hr_id"]
        assert "POL-HR-2026-A" in top.content


def test_7_metadata_filtering_in_bm25_and_hybrid(hybrid_dataset):
    """7. Verify metadata filters are strictly applied to BM25 and hybrid search."""
    with SessionLocal() as db:
        sec_filter = SearchFilters(department="Security")
        resp_sec = hybrid_retriever.search(
            db=db,
            query="policy access credentials",
            top_k=5,
            filters=sec_filter,
            mode=RetrievalMode.HYBRID,
        )
        assert resp_sec.total_results > 0
        for res in resp_sec.results:
            assert res.department == "Security"

        docx_filter = SearchFilters(document_type="docx")
        resp_docx = hybrid_retriever.search(
            db=db,
            query="database standby error",
            top_k=5,
            filters=docx_filter,
            mode=RetrievalMode.BM25,
        )
        assert resp_docx.total_results > 0
        for res in resp_docx.results:
            assert res.document_type == "docx"


# ---------------------------------------------------------------------------
# Index Lifecycle Tests: Rebuilding & Reprocessing Stale Index Removal
# ---------------------------------------------------------------------------

def test_8_rebuilding_bm25_index_from_database(hybrid_dataset):
    """8. Verify bm25_index.rebuild_from_db fully restores index state from PostgreSQL."""
    bm25_index.clear()
    assert bm25_index.size() == 0

    with SessionLocal() as db:
        rebuilt_count = bm25_index.rebuild_from_db(db)
        assert rebuilt_count >= 8
        assert bm25_index.size() >= 8

        matches = bm25_index.search("vacation annual leave", top_k=2)
        assert len(matches) > 0
        assert matches[0]["point_id"] == hybrid_dataset["chunk_hr_id"]


def test_9_reprocessing_document_removes_stale_bm25_entries(hybrid_dataset):
    """9. Verify reprocessing or updating a document removes old BM25 chunks and indexes new ones."""
    with SessionLocal() as db:
        doc_id = hybrid_dataset["doc_hr_id"]
        doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()

        new_chunk_id = uuid.uuid4()
        new_chunk = DocumentChunk(
            id=new_chunk_id,
            document_id=uuid.UUID(doc_id),
            chunk_index=0,
            content="Updated Clause POL-HR-NEW: Employees now receive 25 days of vacation leave.",
            page_number=1,
            end_page=1,
            section="Updated Vacation Clause",
        )

        bm25_index.index_document_chunks(
            document_id=doc_id,
            chunks=[new_chunk],
            document=doc,
        )

        res_new = bm25_index.search("POL-HR-NEW", top_k=2)
        assert len(res_new) > 0
        assert res_new[0]["point_id"] == str(new_chunk_id)

        res_old = bm25_index.search("POL-HR-2026-A", top_k=2)
        old_ids = [m["point_id"] for m in res_old]
        assert hybrid_dataset["chunk_hr_id"] not in old_ids

        bm25_index.rebuild_from_db(db)


# ---------------------------------------------------------------------------
# API Contract & Hybrid Search Endpoint Tests
# ---------------------------------------------------------------------------

def test_10_search_endpoint_hybrid_mode_default(hybrid_dataset):
    """10. Verify POST /api/v1/search uses hybrid mode by default and returns structured schema."""
    req_payload = {
        "query": "What is the annual leave vacation policy?",
        "top_k": 3,
    }
    res = client.post("/api/v1/search", json=req_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "hybrid"
    assert data["query"] == "What is the annual leave vacation policy?"
    assert data["total_results"] > 0
    first = data["results"][0]
    assert "chunk_id" in first
    assert "score" in first
    assert "content" in first
    assert "filename" in first
    assert "department" in first


def test_11_search_endpoint_supports_all_modes(hybrid_dataset):
    """11. Verify POST /api/v1/search explicitly supports 'semantic', 'bm25', and 'hybrid' modes."""
    res_sem = client.post("/api/v1/search", json={"query": "annual leave", "mode": "semantic"})
    assert res_sem.status_code == 200
    assert res_sem.json()["mode"] == "semantic"

    res_bm25 = client.post("/api/v1/search", json={"query": "ERR-DB-504", "mode": "bm25"})
    assert res_bm25.status_code == 200
    assert res_bm25.json()["mode"] == "bm25"

    res_hyb = client.post("/api/v1/search", json={"query": "YubiKey MFA", "mode": "hybrid"})
    assert res_hyb.status_code == 200
    assert res_hyb.json()["mode"] == "hybrid"


# ---------------------------------------------------------------------------
# Information Retrieval Evaluation Benchmark (Precision@K, Recall@K, MRR)
# ---------------------------------------------------------------------------

def test_12_comparative_retrieval_evaluation(hybrid_dataset):
    """12. Evaluate Semantic vs BM25 vs Hybrid on deterministic conceptual, technical, synonym, multi-target & zero-match queries."""
    evaluation_queries = [
        {
            "query": "ERR-DB-504",
            "archetype": "Exact Code Identifier",
            "relevant_ids": {hybrid_dataset["chunk_it_id"]},
        },
        {
            "query": "POL-HR-2026-A",
            "archetype": "Exact Policy Identifier",
            "relevant_ids": {hybrid_dataset["chunk_hr_id"]},
        },
        {
            "query": "paid sick leave and health days for employee doctor visits",
            "archetype": "Vocabulary Mismatch / Synonym",
            "relevant_ids": {hybrid_dataset["chunk_hr_sick_id"]},
        },
        {
            "query": "remote corporate VPN access requirements and credentials",
            "archetype": "Multi-Relevant Target",
            "relevant_ids": {hybrid_dataset["chunk_sec_id"], hybrid_dataset["chunk_sec_pw_id"]},
        },
        {
            "query": "How many days off can staff take for annual summer holidays?",
            "archetype": "Conceptual Semantic Paraphrase",
            "relevant_ids": {hybrid_dataset["chunk_hr_id"]},
        },
        {
            "query": "quantum computing entanglement teleportation protocol",
            "archetype": "Out-of-Domain Zero-Match",
            "relevant_ids": set(),
        },
    ]

    modes = [RetrievalMode.SEMANTIC, RetrievalMode.BM25, RetrievalMode.HYBRID]
    mode_metrics: Dict[RetrievalMode, List[EvaluationMetrics]] = {m: [] for m in modes}
    detailed_results = []

    with SessionLocal() as db:
        for item in evaluation_queries:
            q = item["query"]
            rel = item["relevant_ids"]
            arch = item["archetype"]

            query_detail = {
                "query": q,
                "archetype": arch,
                "relevant_ids": rel,
                "rankings": {},
            }

            for mode in modes:
                resp = hybrid_retriever.search(
                    db=db,
                    query=q,
                    top_k=3,
                    mode=mode,
                    enable_rerank=False,
                )
                retrieved_ids = [r.chunk_id for r in resp.results]
                metrics = compute_retrieval_metrics(
                    retrieved_chunk_ids=retrieved_ids,
                    relevant_chunk_ids=rel,
                    k=3,
                )
                mode_metrics[mode].append(metrics)
                query_detail["rankings"][mode] = {
                    "retrieved_ids": retrieved_ids,
                    "metrics": metrics,
                }

            detailed_results.append(query_detail)

    # Print comprehensive evaluation log
    print("\n" + "=" * 90)
    print("CLARIO PHASE 7: HYBRID RETRIEVAL COMPARATIVE EVALUATION")
    print("=" * 90)
    for qd in detailed_results:
        print(f"\nQuery: '{qd['query']}'")
        print(f"Archetype: {qd['archetype']}")
        rel_str = ", ".join(qd["relevant_ids"]) if qd["relevant_ids"] else "NONE (Zero-match query)"
        print(f"Ground-Truth Relevant Chunk IDs: {rel_str}")
        print("-" * 90)
        for mode in modes:
            r_info = qd["rankings"][mode]
            m: EvaluationMetrics = r_info["metrics"]
            ret_chunks = []
            for rank_idx, cid in enumerate(r_info["retrieved_ids"], start=1):
                match_tag = "[MATCH]" if cid in qd["relevant_ids"] else "[NON-MATCH]"
                ret_chunks.append(f"#{rank_idx} {cid[:8]}... {match_tag}")
            ret_str = " | ".join(ret_chunks) if ret_chunks else "No results retrieved"
            print(f"  {mode.value.upper():<9} -> {ret_str}")
            print(f"            P@3: {m.precision_at_k:.4f} | Recall@3: {m.recall_at_k:.4f} | MRR: {m.mrr:.4f}")

    print("\n" + "=" * 90)
    print("MACRO BENCHMARK METRICS SUMMARY (Across All 6 Queries)")
    print("=" * 90)
    for mode in modes:
        macro_m = compute_macro_retrieval_metrics(mode_metrics[mode])
        print(f"Mode: {mode.value.upper():<10} | Macro P@3: {macro_m.precision_at_k:.4f} | Macro Recall@3: {macro_m.recall_at_k:.4f} | Macro MRR: {macro_m.mrr:.4f}")
    print("=" * 90 + "\n")

    # Assert that all modes execute successfully
    hybrid_macro = compute_macro_retrieval_metrics(mode_metrics[RetrievalMode.HYBRID])
    assert hybrid_macro.mrr >= 0.75


def test_13_macro_metric_aggregation_regression(hybrid_dataset):
    """13. Regression test verifying macro Precision@3, Recall@3, and MRR calculations across 6 queries."""
    evaluation_queries = [
        {"query": "ERR-DB-504", "rel": {hybrid_dataset["chunk_it_id"]}},
        {"query": "POL-HR-2026-A", "rel": {hybrid_dataset["chunk_hr_id"]}},
        {"query": "paid sick leave and health days for employee doctor visits", "rel": {hybrid_dataset["chunk_hr_sick_id"]}},
        {"query": "remote corporate VPN access requirements and credentials", "rel": {hybrid_dataset["chunk_sec_id"], hybrid_dataset["chunk_sec_pw_id"]}},
        {"query": "How many days off can staff take for annual summer holidays?", "rel": {hybrid_dataset["chunk_hr_id"]}},
        {"query": "quantum computing entanglement teleportation protocol", "rel": set()},
    ]

    with SessionLocal() as db:
        for mode, exp_p, exp_r, exp_mrr in [
            (RetrievalMode.SEMANTIC, 0.3333, 0.8333, 0.8333),
            (RetrievalMode.BM25, 0.3333, 0.8333, 0.7500),
            (RetrievalMode.HYBRID, 0.3333, 0.8333, 0.7500),
        ]:
            metrics_list = []
            for item in evaluation_queries:
                resp = hybrid_retriever.search(
                    db=db,
                    query=item["query"],
                    top_k=3,
                    mode=mode,
                    enable_rerank=False,
                )
                ids = [r.chunk_id for r in resp.results]
                m = compute_retrieval_metrics(retrieved_chunk_ids=ids, relevant_chunk_ids=item["rel"], k=3)
                metrics_list.append(m)

            macro = compute_macro_retrieval_metrics(metrics_list)
            assert math.isclose(macro.precision_at_k, exp_p, abs_tol=1e-4)
            assert math.isclose(macro.recall_at_k, exp_r, abs_tol=1e-4)
            assert math.isclose(macro.mrr, exp_mrr, abs_tol=1e-4)


# ---------------------------------------------------------------------------
# Post-Commit Failure Isolation Tests
# ---------------------------------------------------------------------------

def test_14_post_commit_bm25_failure_does_not_corrupt_db_status():
    """14. Verify that post-commit BM25 in-memory sync failure preserves committed READY status in PostgreSQL."""
    db = SessionLocal()
    doc_id = uuid.uuid4()
    
    # 1. Create uploaded test document file & DB record
    import os
    os.makedirs(f"storage/documents/{doc_id}", exist_ok=True)
    file_path = f"storage/documents/{doc_id}/sample.txt"
    with open(file_path, "w") as f:
        f.write("Incident report INC-TEST-909: Automated database backup finished with zero errors.")

    doc = Document(
        id=doc_id,
        filename="sample.txt",
        title="Sample Incident Report",
        document_type="txt",
        department="IT",
        access_level="internal",
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()

    # 2. Mock BM25 index_document_chunks to simulate post-commit in-memory exception
    with patch("app.services.retrieval.bm25_index.BM25Index.index_document_chunks", side_effect=RuntimeError("Simulated BM25 RAM failure")):
        processed_doc = document_service.process_document(db, str(doc_id))
        
        # Verify document processing returns READY and status in DB is READY
        assert processed_doc.status == DocumentStatus.READY

    # 3. Verify in PostgreSQL that document status is READY (not overwritten to FAILED)
    db.expire_all()
    reloaded_doc = db.query(Document).filter(Document.id == doc_id).first()
    assert reloaded_doc is not None
    assert reloaded_doc.status == DocumentStatus.READY

    # 4. Verify BM25 index was marked uninitialized for safe recovery
    assert not bm25_index.is_initialized()

    # 5. Verify subsequent search triggers rebuild_from_db and successfully searches the newly committed document
    resp = hybrid_retriever.search(
        db=db,
        query="INC-TEST-909",
        top_k=3,
        mode=RetrievalMode.HYBRID,
    )
    assert resp.total_results > 0
    assert any("INC-TEST-909" in r.content for r in resp.results)

    # Cleanup test document
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete(synchronize_session=False)
    db.query(Document).filter(Document.id == doc_id).delete(synchronize_session=False)
    db.commit()
    db.close()
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(f"storage/documents/{doc_id}"):
        os.rmdir(f"storage/documents/{doc_id}")
