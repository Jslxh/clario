import uuid
import pytest
import math
import time
from typing import List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import SentenceTransformerEmbeddingService, embedding_service
from app.services.vector_store import QdrantVectorStore, qdrant_vector_store
from app.services.indexing_service import DocumentIndexingService, indexing_service
from app.services.vector_service import vector_service


def test_1_embedding_service_loads_configured_model():
    """1. Verify embedding service loads configured BAAI/bge-small-en-v1.5 model."""
    service = SentenceTransformerEmbeddingService()
    assert service.model_name == "BAAI/bge-small-en-v1.5"
    assert service.get_dimension() == 384


def test_2_3_sample_text_produces_384_dim_embedding():
    """2 & 3. Verify sample text produces a document embedding with exactly 384 dimensions."""
    sample_text = "Clario enterprise knowledge intelligence platform."
    embeddings = embedding_service.embed_documents([sample_text])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384


def test_2b_query_embedding_interface():
    """2b. Verify embed_query generates a 384-dimensional normalized query vector."""
    query = "What is the security compliance policy?"
    query_vec = embedding_service.embed_query(query)
    assert isinstance(query_vec, list)
    assert len(query_vec) == 384
    # Check L2 normalization
    l2_norm = math.sqrt(sum(x * x for x in query_vec))
    assert math.isclose(l2_norm, 1.0, rel_tol=1e-3)



def test_4_empty_input_handled_correctly():
    """4. Verify empty input list returns empty list without error."""
    embeddings = embedding_service.embed_documents([])
    assert embeddings == []


def test_5_6_multiple_texts_order_and_batch_encoding():
    """5 & 6. Verify multiple texts preserve ordering and batch encoding works."""
    texts = [
        "First document paragraph regarding annual leave policies.",
        "Second document paragraph regarding security guidelines.",
        "Third document paragraph regarding cloud deployment.",
    ]
    embeddings = embedding_service.embed_documents(texts)
    assert len(embeddings) == 3
    for vec in embeddings:
        assert len(vec) == 384
    
    # Assert distinct texts produce distinct vectors
    assert embeddings[0] != embeddings[1]
    assert embeddings[1] != embeddings[2]


def test_7_normalization_behavior_verified():
    """7. Verify L2 normalization of output vectors (norm ~ 1.0 for cosine similarity)."""
    text = "Vector normalization test string for Cosine distance verification."
    vec = embedding_service.embed_documents([text])[0]
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(l2_norm, 1.0, rel_tol=1e-3)


def test_8_determinism_within_tolerance():
    """8. Verify same input produces deterministic embeddings across calls."""
    text = "Deterministic sentence embedding test."
    vec1 = embedding_service.embed_documents([text])[0]
    vec2 = embedding_service.embed_documents([text])[0]
    assert len(vec1) == len(vec2) == 384
    for a, b in zip(vec1, vec2):
        assert math.isclose(a, b, abs_tol=1e-5)


def test_9_qdrant_collection_reachable():
    """9. Verify Qdrant collection is reachable and valid."""
    assert vector_service.check_health() is True
    assert qdrant_vector_store.verify_collection() is True


def test_10_11_upsert_test_vector_and_payload_metadata():
    """10 & 11. Verify test vector upsert and payload metadata in Qdrant."""
    test_chunk_id = str(uuid.uuid4())
    test_doc_id = str(uuid.uuid4())
    sample_vec = embedding_service.embed_documents(["Test payload metadata item."])[0]
    
    payload = {
        "document_id": test_doc_id,
        "chunk_id": test_chunk_id,
        "page_number": 1,
        "end_page": 1,
        "section": "Overview",
        "department": "Engineering",
        "document_type": "pdf",
        "access_level": "internal",
        "filename": "architecture.pdf",
    }
    
    point = {
        "point_id": test_chunk_id,
        "vector": sample_vec,
        "payload": payload,
    }
    
    success = qdrant_vector_store.upsert_chunk_vectors([point])
    assert success is True
    
    # Verify retrieval from Qdrant by Point ID
    client = vector_service.get_client()
    retrieved = client.retrieve(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        ids=[test_chunk_id],
    )
    assert len(retrieved) == 1
    assert retrieved[0].payload["document_id"] == test_doc_id
    assert retrieved[0].payload["department"] == "Engineering"
    assert retrieved[0].payload["filename"] == "architecture.pdf"

    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=PointIdsList(points=[test_chunk_id]),
    )


def test_12_reindexing_same_chunk_is_idempotent():
    """12. Verify re-indexing the same chunk updates existing point without duplication."""
    test_chunk_id = str(uuid.uuid4())
    test_doc_id = str(uuid.uuid4())
    sample_vec = embedding_service.embed_documents(["Idempotent indexing content."])[0]
    
    payload = {
        "document_id": test_doc_id,
        "chunk_id": test_chunk_id,
        "page_number": 1,
        "end_page": 1,
        "section": "Initial Section",
        "department": "Security",
        "document_type": "docx",
        "access_level": "internal",
        "filename": "policy.docx",
    }
    
    point = {
        "point_id": test_chunk_id,
        "vector": sample_vec,
        "payload": payload,
    }
    
    # First indexing run
    qdrant_vector_store.upsert_chunk_vectors([point])
    
    # Update payload section and re-index
    point["payload"]["section"] = "Updated Section Title"
    qdrant_vector_store.upsert_chunk_vectors([point])
    
    client = vector_service.get_client()
    retrieved = client.retrieve(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        ids=[test_chunk_id],
    )
    assert len(retrieved) == 1  # No duplicate points created
    assert retrieved[0].payload["section"] == "Updated Section Title"

    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=PointIdsList(points=[test_chunk_id]),
    )


def test_13_incorrect_vector_dimension_rejected():
    """13. Verify vector with incorrect dimension (e.g., 128 instead of 384) is rejected."""
    wrong_vec = [0.1] * 128
    point = {
        "point_id": str(uuid.uuid4()),
        "vector": wrong_vec,
        "payload": {
            "document_id": str(uuid.uuid4()),
            "chunk_id": str(uuid.uuid4()),
            "document_type": "pdf",
            "access_level": "internal",
        },
    }
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        qdrant_vector_store.upsert_chunk_vectors([point])


def test_14_invalid_document_uuid_rejected():
    """14. Verify invalid document UUID in indexing service raises clear ValueError."""
    db = SessionLocal()
    try:
        with pytest.raises(ValueError, match="Invalid document UUID"):
            indexing_service.index_document_chunks(db, "invalid-uuid-string")
    finally:
        db.close()
