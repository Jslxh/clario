import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_ADMIN, ROLE_ANALYST, ROLE_USER
from app.models.audit_log import AuditLog
from app.services.audit_service import audit_service, sanitize_details
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
def audit_users(db: Session):
    admin_role = db.query(Role).filter(Role.name == ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
    analyst_role = db.query(Role).filter(Role.name == ROLE_ANALYST).first() or Role(name=ROLE_ANALYST)
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add_all([admin_role, analyst_role, user_role])
    db.flush()

    uid = uuid.uuid4().hex[:6]
    admin = User(
        email=f"audit_admin_{uid}@clario.enterprise",
        name="Audit Admin",
        password_hash=hash_password("AdminPass123!"),
        department="Executive",
        is_active=True,
    )
    admin.roles.append(admin_role)

    analyst = User(
        email=f"audit_analyst_{uid}@clario.enterprise",
        name="Audit Analyst",
        password_hash=hash_password("AnalystPass123!"),
        department="Analytics",
        is_active=True,
    )
    analyst.roles.append(analyst_role)

    standard_user = User(
        email=f"audit_user_{uid}@clario.enterprise",
        name="Audit User",
        password_hash=hash_password("UserPass123!"),
        department="Engineering",
        is_active=True,
    )
    standard_user.roles.append(user_role)

    db.add_all([admin, analyst, standard_user])
    db.commit()

    token_admin = create_access_token(
        subject=str(admin.id),
        email=admin.email,
        roles=["admin"],
        department=admin.department,
    )
    token_analyst = create_access_token(
        subject=str(analyst.id),
        email=analyst.email,
        roles=["analyst"],
        department=analyst.department,
    )
    token_user = create_access_token(
        subject=str(standard_user.id),
        email=standard_user.email,
        roles=["user"],
        department=standard_user.department,
    )

    return {
        "admin": admin,
        "analyst": analyst,
        "user": standard_user,
        "token_admin": token_admin,
        "token_analyst": token_analyst,
        "token_user": token_user,
    }


def test_sanitize_details_never_stores_secrets():
    """Verify secrets, passwords, tokens, API keys, and JWTs are stripped or redacted."""
    raw_details = {
        "email": "user@example.com",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
        "api_key": "sk-1234567890",
        "jwt": "header.payload.signature",
        "nested": {
            "client_secret": "my-secret-val",
            "normal_field": "keep-this",
        },
        "query": "What is our company budget?",
    }

    sanitized = sanitize_details(raw_details)
    assert sanitized["email"] == "user@example.com"
    assert sanitized["query"] == "What is our company budget?"
    assert sanitized["nested"]["normal_field"] == "keep-this"

    # Verify secret fields are completely stripped
    assert "password" not in sanitized
    assert "access_token" not in sanitized
    assert "api_key" not in sanitized
    assert "jwt" not in sanitized
    assert "client_secret" not in sanitized["nested"]


def test_login_audit_event_logged(db: Session, audit_users):
    """Logging in must create an audit log event without storing the password."""
    user = audit_users["user"]
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    # Query audit logs for login action
    log = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id, AuditLog.action == "login")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log is not None
    assert log.action == "login"
    assert "UserPass123!" not in str(log.details)
    assert log.details.get("email") == user.email


def test_document_upload_and_delete_audit_logging(db: Session, audit_users):
    """Uploading and deleting documents must generate audit events."""
    headers_admin = {"Authorization": f"Bearer {audit_users['token_admin']}"}

    # Upload document
    pdf_content = b"%PDF-1.4 Audit test document content"
    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_admin,
        files={"file": ("audit_doc.pdf", pdf_content, "application/pdf")},
        data={"title": "Audit Doc", "department": "Executive"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Verify upload audit log
    upload_log = (
        db.query(AuditLog)
        .filter(AuditLog.resource_id == doc_id, AuditLog.action == "upload")
        .first()
    )
    assert upload_log is not None
    assert upload_log.resource_type == "document"
    assert upload_log.details.get("filename") == "audit_doc.pdf"

    # Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_admin)
    assert del_res.status_code == 204

    # Verify delete audit log
    delete_log = (
        db.query(AuditLog)
        .filter(AuditLog.resource_id == doc_id, AuditLog.action == "delete")
        .first()
    )
    assert delete_log is not None
    assert delete_log.action == "delete"


def test_audit_logs_endpoint_rbac_and_pagination(db: Session, audit_users):
    """GET /api/v1/audit-logs must enforce RBAC (admin/analyst allowed, user/unauthenticated forbidden)."""
    headers_admin = {"Authorization": f"Bearer {audit_users['token_admin']}"}
    headers_analyst = {"Authorization": f"Bearer {audit_users['token_analyst']}"}
    headers_user = {"Authorization": f"Bearer {audit_users['token_user']}"}

    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/v1/audit-logs")
    assert res_unauth.status_code == 401

    # 2. Regular user -> 403 Forbidden
    res_user = client.get("/api/v1/audit-logs", headers=headers_user)
    assert res_user.status_code == 403

    # 3. Analyst -> 200 OK
    res_analyst = client.get("/api/v1/audit-logs?limit=5&skip=0", headers=headers_analyst)
    assert res_analyst.status_code == 200
    data_analyst = res_analyst.json()
    assert isinstance(data_analyst, list)
    assert len(data_analyst) <= 5

    # 4. Admin -> 200 OK with action filter
    res_admin = client.get("/api/v1/audit-logs?action=login", headers=headers_admin)
    assert res_admin.status_code == 200
    items_admin = res_admin.json()
    assert isinstance(items_admin, list)
    for item in items_admin:
        assert item["action"] == "login"
