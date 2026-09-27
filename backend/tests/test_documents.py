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
