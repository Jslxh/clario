import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models.user import User, Role
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.audit import AuditLog
from app.services.vector_service import vector_service
from app.schemas.vector import QdrantVectorPayload


def test_postgresql_connection():
    """Verify raw PostgreSQL database connectivity."""
    with SessionLocal() as db:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_database_models_and_foreign_keys():
    """Verify table creation, inserts, and foreign key relationships."""
    with SessionLocal() as db:
        # Create test Role
        role = Role(
            name=f"test_role_{uuid.uuid4().hex[:6]}",
            description="Test engineering role",
        )
        db.add(role)
        db.flush()

        # Create test User
        user = User(
            email=f"user_{uuid.uuid4().hex[:6]}@clario.ai",
            name="Alice Test",
            password_hash="pbkdf2_sha256_hash_value",
            department="Engineering",
            is_active=True,
        )
        user.roles.append(role)
        db.add(user)
        db.flush()

        # Create test Document associated with User
        doc = Document(
            filename="q3_architecture.pdf",
            title="Q3 System Architecture Plan",
            document_type="pdf",
            department="Engineering",
            access_level="internal",
            file_path="/storage/docs/q3_architecture.pdf",
            file_size=1048576,
            status=DocumentStatus.UPLOADED,
            uploaded_by=user.id,
        )
        db.add(doc)
        db.flush()

        # Create test DocumentChunk associated with Document
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Vector DB schema design for enterprise knowledge base.",
            page_number=1,
            section="Executive Summary",
        )
        db.add(chunk)

        # Create test AuditLog associated with User
        audit = AuditLog(
            user_id=user.id,
            action="DOCUMENT_UPLOAD",
            resource_type="document",
            resource_id=str(doc.id),
            details={"filename": doc.filename, "size": doc.file_size},
        )
        db.add(audit)

        db.commit()

        # Query & Verify Relationships
        queried_user = db.scalar(select(User).where(User.id == user.id))
        assert queried_user is not None
        assert queried_user.email == user.email
        assert len(queried_user.roles) == 1
        assert queried_user.roles[0].name == role.name

        assert len(queried_user.documents) == 1
        assert queried_user.documents[0].title == "Q3 System Architecture Plan"

        assert len(queried_user.documents[0].chunks) == 1
        assert queried_user.documents[0].chunks[0].chunk_index == 0
        assert "Vector DB" in queried_user.documents[0].chunks[0].content

        assert len(queried_user.audit_logs) == 1
        assert queried_user.audit_logs[0].action == "DOCUMENT_UPLOAD"

        # Cleanup test data
        db.delete(user)  # Cascades to documents, chunks; sets null on audit log
        db.delete(role)
        db.delete(audit)
        db.commit()


def test_qdrant_service_abstraction():
    """Verify Qdrant client payload validation and connectivity service abstraction."""
    payload_data = {
        "document_id": str(uuid.uuid4()),
        "chunk_id": str(uuid.uuid4()),
        "page_number": 2,
        "section": "Data Model",
        "department": "Engineering",
        "document_type": "pdf",
        "access_level": "internal",
    }
    validated_payload = vector_service.validate_payload(payload_data)
    assert validated_payload.document_type == "pdf"
    assert validated_payload.access_level == "internal"

    # Test Qdrant connectivity if container is running
    is_healthy = vector_service.check_health()
    if is_healthy:
        assert vector_service.ensure_collection_exists() is True
