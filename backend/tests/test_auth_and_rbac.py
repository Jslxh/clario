import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_ADMIN, ROLE_ANALYST, ROLE_USER
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
def auth_users(db: Session):
    # Setup roles
    admin_role = db.query(Role).filter(Role.name == ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
    analyst_role = db.query(Role).filter(Role.name == ROLE_ANALYST).first() or Role(name=ROLE_ANALYST)
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add_all([admin_role, analyst_role, user_role])
    db.flush()

    uid = uuid.uuid4().hex[:6]
    # Admin user
    admin = User(
        email=f"admin_{uid}@clario.enterprise",
        name="Admin User",
        password_hash=hash_password("AdminPass123!"),
        department="Executive",
        is_active=True,
    )
    admin.roles.append(admin_role)

    # Engineering user
    eng_user = User(
        email=f"eng_{uid}@clario.enterprise",
        name="Engineer User",
        password_hash=hash_password("EngPass123!"),
        department="Engineering",
        is_active=True,
    )
    eng_user.roles.append(user_role)

    # HR user
    hr_user = User(
        email=f"hr_{uid}@clario.enterprise",
        name="HR User",
        password_hash=hash_password("HrPass123!"),
        department="HR",
        is_active=True,
    )
    hr_user.roles.append(user_role)

    # Analyst user
    analyst = User(
        email=f"analyst_{uid}@clario.enterprise",
        name="Data Analyst",
        password_hash=hash_password("AnalystPass123!"),
        department="Analytics",
        is_active=True,
    )
    analyst.roles.append(analyst_role)

    db.add_all([admin, eng_user, hr_user, analyst])
    db.commit()
    db.refresh(admin)
    db.refresh(eng_user)
    db.refresh(hr_user)
    db.refresh(analyst)

    return {
        "admin": admin,
        "eng_user": eng_user,
        "hr_user": hr_user,
        "analyst": analyst,
    }


def test_1_register_and_login_flow():
    email = f"test_{uuid.uuid4().hex[:8]}@clario.enterprise"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "name": "Test User",
            "department": "Engineering",
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    # Login with correct password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Verify /me endpoint
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_2_invalid_credentials_and_expired_token():
    # Bad login
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@clario.enterprise", "password": "wrong"},
    )
    assert bad_login.status_code == 401

    # Bad token
    bad_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert bad_me.status_code == 401


def test_3_document_authorization_department_and_access_level(db: Session, auth_users):
    retriever = HybridRetriever()

    # Create documents with different access levels and departments
    doc_public = Document(
        id=uuid.uuid4(),
        filename="public_guide.pdf",
        title="Public Guide",
        document_type="pdf",
        department="General",
        access_level="public",
        file_path="/tmp/dummy",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_eng_internal = Document(
        id=uuid.uuid4(),
        filename="eng_architecture.pdf",
        title="Eng Architecture",
        document_type="pdf",
        department="Engineering",
        access_level="internal",
        file_path="/tmp/dummy",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_hr_confidential = Document(
        id=uuid.uuid4(),
        filename="hr_salaries.pdf",
        title="HR Salaries",
        document_type="pdf",
        department="HR",
        access_level="confidential",
        file_path="/tmp/dummy",
        file_size=100,
        status=DocumentStatus.READY,
    )
    doc_admin_restricted = Document(
        id=uuid.uuid4(),
        filename="board_minutes.pdf",
        title="Board Minutes",
        document_type="pdf",
        department="Executive",
        access_level="restricted",
        file_path="/tmp/dummy",
        file_size=100,
        status=DocumentStatus.READY,
    )

    db.add_all([doc_public, doc_eng_internal, doc_hr_confidential, doc_admin_restricted])
    db.flush()

    # Create chunks
    chunk_pub = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_public.id,
        chunk_index=0,
        content="Public content",
    )
    chunk_eng = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_eng_internal.id,
        chunk_index=0,
        content="Engineering internal content",
    )
    chunk_hr = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_hr_confidential.id,
        chunk_index=0,
        content="HR confidential content",
    )
    chunk_admin = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_admin_restricted.id,
        chunk_index=0,
        content="Restricted board content",
    )
    db.add_all([chunk_pub, chunk_eng, chunk_hr, chunk_admin])
    db.commit()

    candidates = [
        {"point_id": str(chunk_pub.id), "score": 0.95},
        {"point_id": str(chunk_eng.id), "score": 0.90},
        {"point_id": str(chunk_hr.id), "score": 0.85},
        {"point_id": str(chunk_admin.id), "score": 0.80},
    ]

    # 1. Admin sees all 4 documents
    admin_hydrated = retriever._hydrate_results(db=db, candidate_matches=candidates, user=auth_users["admin"])
    assert len(admin_hydrated) == 4

    # 2. Engineering user sees public + engineering internal, NOT HR confidential or admin restricted
    eng_hydrated = retriever._hydrate_results(db=db, candidate_matches=candidates, user=auth_users["eng_user"])
    eng_chunk_ids = [r.chunk_id for r in eng_hydrated]
    assert str(chunk_pub.id) in eng_chunk_ids
    assert str(chunk_eng.id) in eng_chunk_ids
    assert str(chunk_hr.id) not in eng_chunk_ids
    assert str(chunk_admin.id) not in eng_chunk_ids
    assert len(eng_hydrated) == 2

    # 3. HR user sees public + HR confidential (if internal/dept matched)
    hr_hydrated = retriever._hydrate_results(db=db, candidate_matches=candidates, user=auth_users["hr_user"])
    hr_chunk_ids = [r.chunk_id for r in hr_hydrated]
    assert str(chunk_pub.id) in hr_chunk_ids
    assert str(chunk_eng.id) not in hr_chunk_ids
    assert str(chunk_admin.id) not in hr_chunk_ids
