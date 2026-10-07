import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_ADMIN, ROLE_USER
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.retrieval.hybrid_retriever import HybridRetriever

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def rbac_fixtures(db: Session):
    admin_role = db.query(Role).filter(Role.name == ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add_all([admin_role, user_role])
    db.flush()

    uid = uuid.uuid4().hex[:6]
    admin = User(
        email=f"admin_sec_{uid}@clario.enterprise",
        name="Admin Sec",
        password_hash=hash_password("Pass123!"),
        department="Executive",
        is_active=True,
    )
    admin.roles.append(admin_role)

    eng_user = User(
        email=f"eng_sec_{uid}@clario.enterprise",
        name="Eng Sec",
        password_hash=hash_password("Pass123!"),
        department="Engineering",
        is_active=True,
    )
    eng_user.roles.append(user_role)

    db.add_all([admin, eng_user])
    db.commit()

    token_admin = create_access_token(
        subject=str(admin.id),
        email=admin.email,
        roles=["admin"],
        department=admin.department,
    )
    token_eng = create_access_token(
        subject=str(eng_user.id),
        email=eng_user.email,
        roles=["user"],
        department=eng_user.department,
    )

    # Create documents
    doc_pub = Document(
        id=uuid.uuid4(),
        filename="company_handbook_public.pdf",
        title="Public Handbook",
        document_type="pdf",
        department="General",
        access_level="public",
        file_path="/tmp/sec_pub",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_eng = Document(
        id=uuid.uuid4(),
        filename="internal_arch.pdf",
        title="Engineering Architecture",
        document_type="pdf",
        department="Engineering",
        access_level="internal",
        file_path="/tmp/sec_eng",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_hr = Document(
        id=uuid.uuid4(),
        filename="executive_salaries.pdf",
        title="Executive Salaries",
        document_type="pdf",
        department="HR",
        access_level="confidential",
        file_path="/tmp/sec_hr",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_res = Document(
        id=uuid.uuid4(),
        filename="board_secrets.pdf",
        title="Board Secrets",
        document_type="pdf",
        department="Executive",
        access_level="restricted",
        file_path="/tmp/sec_res",
        file_size=100,
        status=DocumentStatus.READY,
    )
    db.add_all([doc_pub, doc_eng, doc_hr, doc_res])
    db.flush()

    chunk_pub = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_pub.id,
        chunk_index=0,
        content="Public company guidelines for everyone.",
    )
    chunk_eng = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_eng.id,
        chunk_index=0,
        content="Internal microservice deployment procedures.",
    )
    chunk_hr = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_hr.id,
        chunk_index=0,
        content="Confidential payroll and executive compensation figures.",
    )
    chunk_res = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_res.id,
        chunk_index=0,
        content="Restricted acquisition and board merger minutes.",
    )
    db.add_all([chunk_pub, chunk_eng, chunk_hr, chunk_res])
    db.commit()

    try:
        yield {
            "admin": admin,
            "token_admin": token_admin,
            "eng_user": eng_user,
            "token_eng": token_eng,
            "docs": {
                "pub": doc_pub,
                "eng": doc_eng,
                "hr": doc_hr,
                "res": doc_res,
            },
            "chunks": {
                "pub": chunk_pub,
                "eng": chunk_eng,
                "hr": chunk_hr,
                "res": chunk_res,
            },
        }
    finally:
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id.in_([doc_pub.id, doc_eng.id, doc_hr.id, doc_res.id])
        ).delete(synchronize_session=False)
        db.query(Document).filter(
            Document.id.in_([doc_pub.id, doc_eng.id, doc_hr.id, doc_res.id])
        ).delete(synchronize_session=False)
        db.delete(admin)
        db.delete(eng_user)
        db.commit()


def test_retriever_is_user_authorized_for_doc_unauthenticated(rbac_fixtures):
    """Unauthenticated users must strictly only be authorized for 'public' documents."""
    retriever = HybridRetriever()
    docs = rbac_fixtures["docs"]

    # Public document -> True
    assert retriever._is_user_authorized_for_doc(user=None, doc=docs["pub"]) is True

    # Internal document -> False
    assert retriever._is_user_authorized_for_doc(user=None, doc=docs["eng"]) is False

    # Confidential document -> False
    assert retriever._is_user_authorized_for_doc(user=None, doc=docs["hr"]) is False

    # Restricted document -> False
    assert retriever._is_user_authorized_for_doc(user=None, doc=docs["res"]) is False

    # Authenticated user checks
    assert retriever._is_user_authorized_for_doc(user=rbac_fixtures["eng_user"], doc=docs["eng"]) is True
    assert retriever._is_user_authorized_for_doc(user=rbac_fixtures["eng_user"], doc=docs["hr"]) is False
    assert retriever._is_user_authorized_for_doc(user=rbac_fixtures["admin"], doc=docs["hr"]) is True


def test_hydrate_results_unauthenticated_security_filtering(db: Session, rbac_fixtures):
    """HybridRetriever._hydrate_results must filter out non-public documents when user=None."""
    retriever = HybridRetriever()
    candidates = [
        {"point_id": str(rbac_fixtures["chunks"]["pub"].id), "score": 0.99},
        {"point_id": str(rbac_fixtures["chunks"]["eng"].id), "score": 0.95},
        {"point_id": str(rbac_fixtures["chunks"]["hr"].id), "score": 0.90},
        {"point_id": str(rbac_fixtures["chunks"]["res"].id), "score": 0.85},
    ]

    # Unauthenticated user
    unauth_results = retriever._hydrate_results(db=db, candidate_matches=candidates, user=None)
    assert len(unauth_results) == 1
    assert unauth_results[0].chunk_id == str(rbac_fixtures["chunks"]["pub"].id)
    assert unauth_results[0].filename == "company_handbook_public.pdf"
    assert unauth_results[0].access_level == "public"

    # Authenticated Engineering user -> pub + eng (2 results)
    eng_results = retriever._hydrate_results(db=db, candidate_matches=candidates, user=rbac_fixtures["eng_user"])
    eng_chunk_ids = [r.chunk_id for r in eng_results]
    assert len(eng_results) == 2
    assert str(rbac_fixtures["chunks"]["pub"].id) in eng_chunk_ids
    assert str(rbac_fixtures["chunks"]["eng"].id) in eng_chunk_ids
    assert str(rbac_fixtures["chunks"]["hr"].id) not in eng_chunk_ids
    assert str(rbac_fixtures["chunks"]["res"].id) not in eng_chunk_ids

    # Authenticated Admin -> all 4 results
    admin_results = retriever._hydrate_results(db=db, candidate_matches=candidates, user=rbac_fixtures["admin"])
    assert len(admin_results) == 4


def test_search_endpoint_unauthenticated_security_boundary(db: Session, rbac_fixtures):
    """POST /api/v1/search without authorization token must only return public documents."""
    mock_retrieval_candidates = [
        {"point_id": str(rbac_fixtures["chunks"]["pub"].id), "score": 0.99},
        {"point_id": str(rbac_fixtures["chunks"]["hr"].id), "score": 0.95},
    ]

    with patch("app.services.retrieval.hybrid_retriever.hybrid_retriever.semantic_retriever.vector_store.search_vectors", return_value=mock_retrieval_candidates):
        with patch("app.services.retrieval.hybrid_retriever.hybrid_retriever.bm25_index.search", return_value=[]):
            # Unauthenticated search request
            resp = client.post("/api/v1/search", json={"query": "salaries guidelines", "top_k": 10})
            assert resp.status_code == 200
            data = resp.json()
            results = data["results"]
            # Confidential HR doc must be blocked! Only public returned.
            for res in results:
                assert res["filename"] != "executive_salaries.pdf"
            assert any(res["filename"] == "company_handbook_public.pdf" for res in results)

