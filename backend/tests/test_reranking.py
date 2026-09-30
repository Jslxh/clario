import uuid
import math
import time
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
from app.services.embeddings import embedding_service
from app.services.vector_store import qdrant_vector_store
from app.services.retrieval import (
    RetrievalMode,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    RetrievalResult,
    bm25_index,
    hybrid_retriever,
    compute_retrieval_metrics,
    compute_macro_retrieval_metrics,
    EvaluationMetrics,
)
from app.services.reranking import (
    BaseReranker,
    CrossEncoderReranker,
    reranker_service,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixture: Seed deterministic 8-chunk dataset for reranking evaluation
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rerank_dataset():
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
# Unit & Edge Case Tests for CrossEncoderReranker
# ---------------------------------------------------------------------------

def test_1_cross_encoder_lazy_loading():
    """1. Verify CrossEncoderReranker does not load the model until first rerank call."""
    custom_reranker = CrossEncoderReranker()
    assert not custom_reranker.is_model_loaded()

    # Create dummy candidate
    sample_candidate = RetrievalResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        score=0.85,
        content="Vacation policy provides 18 days leave.",
        filename="policy.pdf",
        document_type="pdf",
        access_level="internal",
    )

    reranked = custom_reranker.rerank(
        query="vacation leave",
        candidates=[sample_candidate],
        top_k=1,
    )
    assert custom_reranker.is_model_loaded()
    assert len(reranked) == 1


def test_2_cross_encoder_empty_candidates():
    """2. Verify rerank() handles empty candidate lists safely without error."""
    custom_reranker = CrossEncoderReranker()
    result = custom_reranker.rerank(query="annual leave", candidates=[], top_k=5)
    assert result == []


def test_3_cross_encoder_empty_query():
    """3. Verify rerank() handles empty or whitespace queries by returning original slice."""
    c1 = RetrievalResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        score=0.9,
        content="First chunk content",
        filename="f1.pdf",
        document_type="pdf",
        access_level="internal",
    )
    c2 = RetrievalResult(
        chunk_id="chunk-2",
        document_id="doc-2",
        score=0.8,
        content="Second chunk content",
        filename="f2.pdf",
        document_type="pdf",
        access_level="internal",
    )

    reranker = CrossEncoderReranker()
    res = reranker.rerank(query="   ", candidates=[c1, c2], top_k=1)
    assert len(res) == 1
    assert res[0].chunk_id == "chunk-1"


def test_4_cross_encoder_single_candidate():
    """4. Verify reranking a single candidate preserves initial scores and populates rerank_score."""
    c = RetrievalResult(
        chunk_id="chunk-solo",
        document_id="doc-solo",
        score=0.77,
        content="Authentication requires FIDO2 hardware token.",
        filename="sec.pdf",
        document_type="pdf",
        access_level="confidential",
    )
    res = reranker_service.rerank(query="FIDO2 token", candidates=[c], top_k=1)
    assert len(res) == 1
    top = res[0]
    assert top.chunk_id == "chunk-solo"
    assert top.initial_score == 0.77
    assert top.initial_rank == 1
    assert top.rerank_score is not None
    assert top.score == top.rerank_score


def test_5_cross_encoder_fewer_candidates_than_top_k():
    """5. Verify passing fewer candidates than requested top_k returns all candidates without error."""
    c1 = RetrievalResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        score=0.9,
        content="PostgreSQL high latency pool exhaustion",
        filename="db.docx",
        document_type="docx",
        access_level="internal",
    )
    c2 = RetrievalResult(
        chunk_id="chunk-2",
        document_id="doc-2",
        score=0.7,
        content="Corporate flight travel booking Concur",
        filename="travel.pdf",
        document_type="pdf",
        access_level="internal",
    )
    res = reranker_service.rerank(
        query="PostgreSQL database query latency",
        candidates=[c1, c2],
        top_k=10,
    )
    assert len(res) == 2
    assert res[0].chunk_id == "chunk-1"
    assert res[0].rerank_score > res[1].rerank_score


def test_6_cross_encoder_score_monotonicity_and_annotation():
    """6. Verify returned results are strictly monotonically decreasing by rerank_score."""
    candidates = [
        RetrievalResult(
            chunk_id=f"c-{i}",
            document_id=f"d-{i}",
            score=1.0 - (i * 0.1),
            content=text,
            filename=f"file_{i}.pdf",
            document_type="pdf",
            access_level="internal",
        )
        for i, text in enumerate([
            "Flight expense reimbursement Concur policy.",
            "Standby node database write replication failure error ERR-DB-504.",
            "Annual employee vacation leave 18 statutory days.",
        ])
    ]

    res = reranker_service.rerank(
        query="database standby replication error ERR-DB-504",
        candidates=candidates,
        top_k=3,
    )
    assert len(res) == 3
    # Verify strict descending order
    for i in range(len(res) - 1):
        assert res[i].rerank_score >= res[i + 1].rerank_score

    # Confirm the relevant chunk (c-1, standby DB) was promoted to #1
    assert res[0].chunk_id == "c-1"
    assert res[0].initial_rank == 2  # was rank 2 originally
    assert res[0].initial_score == 0.9


def test_7_cross_encoder_deterministic_output():
    """7. Verify deterministic scoring across identical query and candidate lists."""
    c = RetrievalResult(
        chunk_id="chunk-det",
        document_id="doc-det",
        score=0.88,
        content="Production VPN requires physical FIDO2 YubiKey tokens.",
        filename="sec.pdf",
        document_type="pdf",
        access_level="confidential",
    )
    res1 = reranker_service.rerank(query="YubiKey VPN", candidates=[c])
    res2 = reranker_service.rerank(query="YubiKey VPN", candidates=[c])
    assert math.isclose(res1[0].rerank_score, res2[0].rerank_score, rel_tol=1e-5)


def test_8_cross_encoder_fallback_on_error():
    """8. Verify that inference exceptions fall back gracefully to first-stage candidate order."""
    c1 = RetrievalResult(
        chunk_id="c1",
        document_id="d1",
        score=0.9,
        content="Text 1",
        filename="f1.pdf",
        document_type="pdf",
        access_level="internal",
    )
    c2 = RetrievalResult(
        chunk_id="c2",
        document_id="d2",
        score=0.8,
        content="Text 2",
        filename="f2.pdf",
        document_type="pdf",
        access_level="internal",
    )

    fallback_reranker = CrossEncoderReranker(fallback_on_error=True)
    with patch.object(fallback_reranker, "_get_model", side_effect=RuntimeError("Simulated CUDA failure")):
        res = fallback_reranker.rerank(query="test query", candidates=[c1, c2], top_k=2)
        assert len(res) == 2
        assert res[0].chunk_id == "c1"
        assert res[1].chunk_id == "c2"
        assert res[0].rerank_score is None


# ---------------------------------------------------------------------------
# Integration & API Tests with Hybrid Search Endpoint
# ---------------------------------------------------------------------------

def test_9_search_endpoint_with_rerank_toggle(rerank_dataset):
    """9. Verify POST /api/v1/search supports explicit enable_rerank toggle."""
    # 1. Reranking Enabled (Default)
    req_payload_on = {
        "query": "ERR-DB-504 replication failure",
        "top_k": 3,
        "enable_rerank": True,
    }
    res_on = client.post("/api/v1/search", json=req_payload_on)
    assert res_on.status_code == 200
    data_on = res_on.json()
    assert data_on["reranked"] is True
    assert len(data_on["results"]) > 0
    top_on = data_on["results"][0]
    assert "rerank_score" in top_on
    assert "initial_score" in top_on
    assert "initial_rank" in top_on
    assert top_on["chunk_id"] == rerank_dataset["chunk_it_id"]

    # 2. Reranking Disabled (Opt-out)
    req_payload_off = {
        "query": "ERR-DB-504 replication failure",
        "top_k": 3,
        "enable_rerank": False,
    }
    res_off = client.post("/api/v1/search", json=req_payload_off)
    assert res_off.status_code == 200
    data_off = res_off.json()
    assert data_off["reranked"] is False


# ---------------------------------------------------------------------------
# Comparative Quality & Latency Benchmark (Stage 1 vs Stage 2 Reranked)
# ---------------------------------------------------------------------------

def test_10_comparative_reranking_evaluation_and_latency(rerank_dataset):
    """10. Benchmark Stage 1 Hybrid vs Stage 2 Reranked across accuracy metrics and latency."""
    evaluation_queries = [
        {
            "query": "ERR-DB-504",
            "archetype": "Exact Code Identifier",
            "relevant_ids": {rerank_dataset["chunk_it_id"]},
        },
        {
            "query": "POL-HR-2026-A",
            "archetype": "Exact Policy Identifier",
            "relevant_ids": {rerank_dataset["chunk_hr_id"]},
        },
        {
            "query": "paid sick leave and health days for employee doctor visits",
            "archetype": "Vocabulary Mismatch / Synonym",
            "relevant_ids": {rerank_dataset["chunk_hr_sick_id"]},
        },
        {
            "query": "remote corporate VPN access requirements and credentials",
            "archetype": "Multi-Relevant Target",
            "relevant_ids": {rerank_dataset["chunk_sec_id"], rerank_dataset["chunk_sec_pw_id"]},
        },
        {
            "query": "How many days off can staff take for annual summer holidays?",
            "archetype": "Conceptual Semantic Paraphrase",
            "relevant_ids": {rerank_dataset["chunk_hr_id"]},
        },
        {
            "query": "quantum computing entanglement teleportation protocol",
            "archetype": "Out-of-Domain Zero-Match",
            "relevant_ids": set(),
        },
    ]

    metrics_stage1: List[EvaluationMetrics] = []
    metrics_stage2: List[EvaluationMetrics] = []

    stage1_latencies: List[float] = []
    stage2_latencies: List[float] = []

    with SessionLocal() as db:
        for item in evaluation_queries:
            q = item["query"]
            rel = item["relevant_ids"]

            # Stage 1: Hybrid without reranking
            t0 = time.perf_counter()
            resp_s1 = hybrid_retriever.search(
                db=db,
                query=q,
                top_k=3,
                mode=RetrievalMode.HYBRID,
                enable_rerank=False,
            )
            t1 = time.perf_counter()
            stage1_latencies.append((t1 - t0) * 1000.0)

            ids_s1 = [r.chunk_id for r in resp_s1.results]
            m1 = compute_retrieval_metrics(retrieved_chunk_ids=ids_s1, relevant_chunk_ids=rel, k=3)
            metrics_stage1.append(m1)

            # Stage 2: Hybrid with Cross-Encoder Reranking
            t2 = time.perf_counter()
            resp_s2 = hybrid_retriever.search(
                db=db,
                query=q,
                top_k=3,
                mode=RetrievalMode.HYBRID,
                enable_rerank=True,
            )
            t3 = time.perf_counter()
            stage2_latencies.append((t3 - t2) * 1000.0)

            ids_s2 = [r.chunk_id for r in resp_s2.results]
            m2 = compute_retrieval_metrics(retrieved_chunk_ids=ids_s2, relevant_chunk_ids=rel, k=3)
            metrics_stage2.append(m2)

            print(f"\nQuery: '{q}'")
            print(f"  Stage 1 (Hybrid): MRR={m1.mrr:.4f} | {[r.chunk_id[:8] + (' [MATCH]' if r.chunk_id in rel else '') for r in resp_s1.results]}")
            print(f"  Stage 2 (Rerank): MRR={m2.mrr:.4f} | {[r.chunk_id[:8] + (' [MATCH]' if r.chunk_id in rel else '') for r in resp_s2.results]}")
            if resp_s2.results:
                print(f"  Rerank scores: {[round(r.rerank_score, 4) if r.rerank_score is not None else None for r in resp_s2.results]}")

    macro_s1 = compute_macro_retrieval_metrics(metrics_stage1)
    macro_s2 = compute_macro_retrieval_metrics(metrics_stage2)

    avg_lat_s1 = sum(stage1_latencies) / len(stage1_latencies)
    avg_lat_s2 = sum(stage2_latencies) / len(stage2_latencies)

    print("\n" + "=" * 90)
    print("PHASE 8: STAGE 1 (HYBRID) VS STAGE 2 (CROSS-ENCODER RERANKED) COMPARISON")
    print("=" * 90)
    print(f"Stage 1 (Hybrid Baseline): Macro P@3: {macro_s1.precision_at_k:.4f} | Recall@3: {macro_s1.recall_at_k:.4f} | MRR: {macro_s1.mrr:.4f} | Avg Latency: {avg_lat_s1:.2f}ms")
    print(f"Stage 2 (Reranked Hybrid): Macro P@3: {macro_s2.precision_at_k:.4f} | Recall@3: {macro_s2.recall_at_k:.4f} | MRR: {macro_s2.mrr:.4f} | Avg Latency: {avg_lat_s2:.2f}ms")
    print("=" * 90 + "\n")

    assert macro_s2.precision_at_k >= 0.30
    assert macro_s2.recall_at_k >= 0.80
