import os
import io
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.services.file_storage import file_storage_service

client = TestClient(app)


def test_1_valid_pdf_upload():
    """1. Test valid PDF file upload."""
    pdf_content = b"%PDF-1.4 header content for testing PDF uploads"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_report.pdf", pdf_content, "application/pdf")},
        data={
            "title": "Quarterly Financial Report",
            "department": "Finance",
            "access_level": "confidential",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_report.pdf"
    assert data["title"] == "Quarterly Financial Report"
    assert data["document_type"] == "pdf"
    assert data["department"] == "Finance"
    assert data["access_level"] == "confidential"
    assert data["status"] == "uploaded"
    assert data["file_size"] == len(pdf_content)
    assert "storage/documents/" in data["file_path"]

    # Verify physical file existence
    assert os.path.exists(data["file_path"])

    # Cleanup test file
    file_storage_service.delete_file_directory(data["id"])


def test_2_valid_docx_upload():
    """2. Test valid DOCX file upload."""
    docx_content = b"PK\x03\x04 Zip container header for testing DOCX file upload"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("project_proposal.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "Project Proposal"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "project_proposal.docx"
    assert data["document_type"] == "docx"
    assert data["status"] == "uploaded"

    # Cleanup test file
    file_storage_service.delete_file_directory(data["id"])


def test_3_valid_txt_upload():
    """3. Test valid TXT file upload."""
    txt_content = b"Clario enterprise knowledge base document content."
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", txt_content, "text/plain")},
        data={"department": "Engineering"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "notes.txt"
    assert data["document_type"] == "txt"
    assert data["department"] == "Engineering"

    # Cleanup test file
    file_storage_service.delete_file_directory(data["id"])


def test_4_unsupported_extension_rejection():
    """4. Test rejection of unsupported file extensions (e.g. .exe, .py)."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("malicious_script.exe", b"binary content", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_5_empty_file_rejection():
    """5. Test rejection of empty files (0 bytes)."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty_file.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_6_oversized_file_rejection(monkeypatch):
    """6. Test rejection of files exceeding max upload size limit."""
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)
    pdf_content = b"%PDF-1.4 " + b"X" * 200
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("large_document.pdf", pdf_content, "application/pdf")},
    )
    assert response.status_code == 400
    assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_7_filename_sanitization():
    """7. Test filename sanitization preventing dangerous path traversal characters."""
    raw_filename = "../../../etc/passwd_report.pdf"
    pdf_content = b"%PDF-1.4 Valid content header"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": (raw_filename, pdf_content, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert ".." not in data["filename"]
    assert "/" not in data["filename"]
    assert data["filename"] == "passwd_report.pdf"

    # Cleanup
    file_storage_service.delete_file_directory(data["id"])


def test_8_path_traversal_attempt_rejection():
    """8. Test rejection of path traversal in storage service save_file."""
    with pytest.raises(ValueError, match="Path traversal attempt"):
        file_storage_service.save_file(
            document_id="../invalid_dir",
            file_bytes=b"content",
            extension="txt",
        )


def test_9_10_database_record_and_file_existence():
    """9 & 10. Verify document database record creation and physical file existence."""
    pdf_content = b"%PDF-1.4 Verification document"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("verify.pdf", pdf_content, "application/pdf")},
        data={"title": "Verification PDF", "department": "Security"},
    )
    assert response.status_code == 201
    data = response.json()
    doc_id = uuid.UUID(data["id"])

    # Query DB record
    with SessionLocal() as db:
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        assert doc_record is not None
        assert doc_record.filename == "verify.pdf"
        assert doc_record.title == "Verification PDF"
        assert doc_record.status == DocumentStatus.UPLOADED
        assert doc_record.file_size == len(pdf_content)

        # Verify storage file exists on disk
        assert file_storage_service.file_exists(doc_record.file_path)

        # Cleanup test DB record and directory
        db.delete(doc_record)
        db.commit()

    file_storage_service.delete_file_directory(str(doc_id))


def test_11_health_endpoint_still_works():
    """11. Verify GET /health endpoint remains functional."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "clario-backend"


def test_12_process_document_end_to_end_and_idempotency():
    """12. Test end-to-end POST /api/v1/documents/{id}/process and idempotency."""
    txt_content = b"Clario Knowledge Base Section 1: Overview\n\nClario enables enterprise teams to upload and search internal documents."
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("kb_doc.txt", txt_content, "text/plain")},
        data={"title": "KB Document", "department": "Engineering"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Process document
    proc_res1 = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res1.status_code == 200
    data1 = proc_res1.json()
    assert data1["status"] == "ready"

    # Verify chunks in DB
    with SessionLocal() as db:
        from app.models.document_chunk import DocumentChunk
        chunks1 = db.query(DocumentChunk).filter(DocumentChunk.document_id == uuid.UUID(doc_id)).all()
        assert len(chunks1) > 0
        chunk_count1 = len(chunks1)

    # 2. Process document second time (Idempotency check)
    proc_res2 = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res2.status_code == 200
    data2 = proc_res2.json()
    assert data2["status"] == "ready"

    # Verify DB chunk count was not duplicated
    with SessionLocal() as db:
        from app.models.document_chunk import DocumentChunk
        chunks2 = db.query(DocumentChunk).filter(DocumentChunk.document_id == uuid.UUID(doc_id)).all()
        assert len(chunks2) == chunk_count1

        # Cleanup DB doc record
        doc_rec = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
        if doc_rec:
            db.delete(doc_rec)
            db.commit()

    file_storage_service.delete_file_directory(doc_id)


def test_13_process_document_invalid_and_failed_states():
    """13. Test invalid UUID, non-existent doc, and FAILED status transition."""
    # 1. Invalid UUID
    res_inv = client.post("/api/v1/documents/invalid-uuid/process")
    assert res_inv.status_code == 400

    # 2. Non-existent document
    random_id = str(uuid.uuid4())
    res_404 = client.post(f"/api/v1/documents/{random_id}/process")
    assert res_404.status_code == 404

    # 3. Document record exists but file is missing -> FAILED status transition
    with SessionLocal() as db:
        doc_uuid = uuid.uuid4()
        fake_doc = Document(
            id=doc_uuid,
            filename="missing.pdf",
            title="Missing File Doc",
            document_type="pdf",
            file_path="storage/documents/non_existent_file.pdf",
            file_size=100,
            status=DocumentStatus.UPLOADED,
        )
        db.add(fake_doc)
        db.commit()

    res_fail = client.post(f"/api/v1/documents/{doc_uuid}/process")
    assert res_fail.status_code in (404, 500)

    # Verify document status in DB updated to FAILED
    with SessionLocal() as db:
        doc_check = db.query(Document).filter(Document.id == doc_uuid).first()
        assert doc_check is not None
        assert doc_check.status == DocumentStatus.FAILED

        # Cleanup
        db.delete(doc_check)
        db.commit()

