import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.document_service import document_service
from app.services.file_storage import file_storage_service

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_background_processing_success_flow(db: Session):
    """Test successful background document processing: UPLOADED -> PROCESSING -> READY."""
    txt_content = b"Background processing guide.\n\nClario processes enterprise documents asynchronously."
    
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("bg_test.txt", txt_content, "text/plain")},
        data={
            "title": "Background Processing Test",
            "department": "Engineering",
            "access_level": "public",
        },
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Trigger background processing (mock Qdrant indexing so test runs hermetically without external daemon)
    from unittest.mock import patch
    with patch("app.services.indexing_service.indexing_service.index_document_chunks", return_value=True):
        proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        initial_data = proc_res.json()
        # Endpoint immediately transitions status to PROCESSING and returns it
        assert initial_data["status"] == "processing"

    # 2. In FastAPI TestClient, background task executes during response delivery
    # Verify DB record transitioned to READY
    db.expire_all()
    doc_in_db = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    assert doc_in_db is not None
    assert doc_in_db.status == DocumentStatus.READY

    # 3. Verify chunks were persisted to DB
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == uuid.UUID(doc_id)).all()
    assert len(chunks) > 0

    # 4. Verify GET /api/v1/documents/{id} returns READY and chunk_count
    detail_res = client.get(f"/api/v1/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "ready"
    assert detail["chunk_count"] == len(chunks)

    # Cleanup
    file_storage_service.delete_file_directory(doc_id)
    db.delete(doc_in_db)
    db.commit()


def test_background_processing_failure_flow(db: Session):
    """Test failed background processing when original file is missing: transitions to FAILED."""
    doc_uuid = uuid.uuid4()
    doc_id_str = str(doc_uuid)

    # Insert document with non-existent file
    doc_record = Document(
        id=doc_uuid,
        filename="missing_bg.txt",
        title="Missing File For Background Task",
        document_type="txt",
        file_path="storage/documents/non_existent_bg_dir/original.txt",
        file_size=100,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc_record)
    db.commit()

    # Trigger background processing
    proc_res = client.post(f"/api/v1/documents/{doc_id_str}/process")
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "processing"

    # Background task executes and detects missing file -> marks FAILED
    db.expire_all()
    failed_doc = db.query(Document).filter(Document.id == doc_uuid).first()
    assert failed_doc is not None
    assert failed_doc.status == DocumentStatus.FAILED

    # Cleanup
    db.delete(failed_doc)
    db.commit()


def test_background_processing_direct_service_execution(db: Session):
    """Directly test document_service.process_document_background handles errors gracefully."""
    doc_uuid = uuid.uuid4()
    doc_id_str = str(doc_uuid)

    doc_record = Document(
        id=doc_uuid,
        filename="direct_missing.txt",
        title="Direct Missing Test",
        document_type="txt",
        file_path="storage/documents/non_existent_direct/original.txt",
        file_size=50,
        status=DocumentStatus.PROCESSING,
    )
    db.add(doc_record)
    db.commit()

    # Invoke background task handler directly
    document_service.process_document_background(doc_id_str)

    db.expire_all()
    res_doc = db.query(Document).filter(Document.id == doc_uuid).first()
    assert res_doc is not None
    assert res_doc.status == DocumentStatus.FAILED

    # Cleanup
    db.delete(res_doc)
    db.commit()
