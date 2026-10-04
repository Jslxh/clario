import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_ADMIN, ROLE_ANALYST, ROLE_USER
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.file_storage import file_storage_service

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_setup(db: Session):
    admin_role = db.query(Role).filter(Role.name == ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add_all([admin_role, user_role])
    db.flush()

    uid = uuid.uuid4().hex[:6]
    # Admin
    admin_user = User(
        email=f"admin_{uid}@clario.enterprise",
        name="Admin User",
        password_hash=hash_password("Pass123!"),
        department="Executive",
        is_active=True,
    )
    admin_user.roles.append(admin_role)

    # Alice (Engineering)
    alice = User(
        email=f"alice_{uid}@clario.enterprise",
        name="Alice Eng",
        password_hash=hash_password("Pass123!"),
        department="Engineering",
        is_active=True,
    )
    alice.roles.append(user_role)

    # Bob (HR)
    bob = User(
        email=f"bob_{uid}@clario.enterprise",
        name="Bob HR",
        password_hash=hash_password("Pass123!"),
        department="HR",
        is_active=True,
    )
    bob.roles.append(user_role)

    db.add_all([admin_user, alice, bob])
    db.commit()

    token_admin = create_access_token(
        subject=str(admin_user.id),
        email=admin_user.email,
        roles=["admin"],
        department=admin_user.department,
    )
    token_alice = create_access_token(
        subject=str(alice.id),
        email=alice.email,
        roles=["user"],
        department=alice.department,
    )
    token_bob = create_access_token(
        subject=str(bob.id),
        email=bob.email,
        roles=["user"],
        department=bob.department,
    )

    return {
        "admin": admin_user,
        "alice": alice,
        "bob": bob,
        "token_admin": token_admin,
        "token_alice": token_alice,
        "token_bob": token_bob,
    }


def test_list_documents_unauthenticated_only_public(db: Session, test_setup):
    """Unauthenticated users must only see public documents."""
    doc_pub = Document(
        id=uuid.uuid4(),
        filename="public_notice.pdf",
        title="Public Notice",
        document_type="pdf",
        department="General",
        access_level="public",
        file_path="/tmp/p1",
        file_size=120,
        status=DocumentStatus.READY,
    )
    doc_eng = Document(
        id=uuid.uuid4(),
        filename="eng_spec.pdf",
        title="Eng Spec",
        document_type="pdf",
        department="Engineering",
        access_level="internal",
        file_path="/tmp/p2",
        file_size=200,
        status=DocumentStatus.READY,
    )
    db.add_all([doc_pub, doc_eng])
    db.commit()

    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    # All items returned must be public
    assert all(item["access_level"] == "public" for item in items)
    assert any(item["id"] == str(doc_pub.id) for item in items)
    assert not any(item["id"] == str(doc_eng.id) for item in items)


def test_list_documents_rbac_and_filters(db: Session, test_setup):
    """Alice (Engineering) sees public + engineering internal documents, with pagination & filters."""
    doc_alice = Document(
        id=uuid.uuid4(),
        filename="alice_eng.pdf",
        title="Alice Engineering Guide",
        document_type="pdf",
        department="Engineering",
        access_level="internal",
        uploaded_by=test_setup["alice"].id,
        file_path="/tmp/a1",
        file_size=150,
        status=DocumentStatus.READY,
    )
    doc_hr = Document(
        id=uuid.uuid4(),
        filename="hr_salaries.pdf",
        title="HR Salaries",
        document_type="pdf",
        department="HR",
        access_level="confidential",
        uploaded_by=test_setup["bob"].id,
        file_path="/tmp/b1",
        file_size=300,
        status=DocumentStatus.READY,
    )
    db.add_all([doc_alice, doc_hr])
    db.commit()

    headers_alice = {"Authorization": f"Bearer {test_setup['token_alice']}"}

    # Alice listing: should include alice_eng, should NOT include hr_salaries
    resp = client.get("/api/v1/documents?limit=10&skip=0", headers=headers_alice)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    doc_ids = [d["id"] for d in items]
    assert str(doc_alice.id) in doc_ids
    assert str(doc_hr.id) not in doc_ids

    # Alice filter by department=Engineering
    resp_filter = client.get("/api/v1/documents?department=Engineering", headers=headers_alice)
    assert resp_filter.status_code == 200
    for item in resp_filter.json():
        assert item["department"] == "Engineering"

    # Alice filter by status=ready
    resp_status = client.get("/api/v1/documents?status=ready", headers=headers_alice)
    assert resp_status.status_code == 200
    for item in resp_status.json():
        assert item["status"] == "ready"

    # Admin listing: sees everything
    headers_admin = {"Authorization": f"Bearer {test_setup['token_admin']}"}
    resp_admin = client.get("/api/v1/documents", headers=headers_admin)
    assert resp_admin.status_code == 200
    admin_doc_ids = [d["id"] for d in resp_admin.json()]
    assert str(doc_alice.id) in admin_doc_ids
    assert str(doc_hr.id) in admin_doc_ids


def test_get_document_detail_and_authorization(db: Session, test_setup):
    """GET /api/v1/documents/{id} returns metadata, chunk_count, and enforces auth."""
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="detail_test.pdf",
        title="Detail Test Document",
        document_type="pdf",
        department="Engineering",
        access_level="internal",
        uploaded_by=test_setup["alice"].id,
        file_path="/tmp/detail1",
        file_size=500,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    db.flush()

    # Add 3 chunks
    chunks = [
        DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=i, content=f"Chunk {i}")
        for i in range(3)
    ]
    db.add_all(chunks)
    db.commit()

    headers_alice = {"Authorization": f"Bearer {test_setup['token_alice']}"}
    headers_bob = {"Authorization": f"Bearer {test_setup['token_bob']}"}

    # Alice (Engineering, uploader) -> 200 with chunk_count = 3
    resp_alice = client.get(f"/api/v1/documents/{doc_id}", headers=headers_alice)
    assert resp_alice.status_code == 200
    detail = resp_alice.json()
    assert detail["id"] == str(doc_id)
    assert detail["title"] == "Detail Test Document"
    assert detail["chunk_count"] == 3
    assert detail["status"] == "ready"

    # Bob (HR) -> 403 Forbidden
    resp_bob = client.get(f"/api/v1/documents/{doc_id}", headers=headers_bob)
    assert resp_bob.status_code == 403

    # Unauthenticated -> 401 or 403
    resp_unauth = client.get(f"/api/v1/documents/{doc_id}")
    assert resp_unauth.status_code in (401, 403)

    # Invalid UUID
    resp_inv = client.get("/api/v1/documents/not-a-valid-uuid", headers=headers_alice)
    assert resp_inv.status_code == 400

    # Non-existent UUID
    resp_404 = client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=headers_alice)
    assert resp_404.status_code == 404


def test_delete_document_end_to_end(db: Session, test_setup):
    """DELETE /api/v1/documents/{id} handles authorization, DB cascade, Qdrant deletion, and file removal."""
    doc_id = uuid.uuid4()
    
    # Create a real file on disk using storage service
    saved_path = file_storage_service.save_file(
        document_id=str(doc_id),
        file_bytes=b"Content to be deleted on disk",
        extension="txt",
    )
    assert os.path.exists(saved_path)

    doc = Document(
        id=doc_id,
        filename="delete_me.txt",
        title="File To Delete",
        document_type="txt",
        department="Engineering",
        access_level="internal",
        uploaded_by=test_setup["alice"].id,
        file_path=saved_path,
        file_size=28,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    db.flush()

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content="Chunk to delete",
    )
    db.add(chunk)
    db.commit()

    headers_alice = {"Authorization": f"Bearer {test_setup['token_alice']}"}
    headers_bob = {"Authorization": f"Bearer {test_setup['token_bob']}"}

    # Bob (unauthorized non-admin) tries to delete Alice's doc -> 403 Forbidden
    resp_bob = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_bob)
    assert resp_bob.status_code == 403
    # File and DB record must still exist
    assert os.path.exists(saved_path)

    # Alice (uploader) deletes doc -> 204 No Content
    with patch("app.services.vector_store.qdrant_store.qdrant_store.delete_vectors_by_document") as mock_qdrant_del:
        mock_qdrant_del.return_value = True
        resp_del = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_alice)
        assert resp_del.status_code == 204
        mock_qdrant_del.assert_called_once_with(str(doc_id))

    # Verify file deleted from disk
    assert not os.path.exists(saved_path)

    # Verify document and chunk deleted from DB
    doc_in_db = db.query(Document).filter(Document.id == doc_id).first()
    assert doc_in_db is None
    chunks_in_db = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    assert len(chunks_in_db) == 0

    # Non-existent doc delete -> 404
    resp_404 = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_alice)
    assert resp_404.status_code == 404
