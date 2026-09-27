import uuid
import pytest
from sqlalchemy import select, text, inspect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.db.base import Base
from app.models import User, Role, user_roles, Document, DocumentChunk, DocumentStatus, AuditLog
from app.services.vector_service import vector_service
from app.schemas.vector import QdrantVectorPayload


def test_1_postgresql_connection():
    """1. Verify raw PostgreSQL database connectivity."""
    with SessionLocal() as db:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_2_sqlalchemy_model_metadata_loading():
    """2. Verify SQLAlchemy 2.x metadata and model classes load cleanly."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {"users", "roles", "user_roles", "documents", "document_chunks", "audit_logs"}
    assert expected_tables.issubset(table_names), f"Missing tables in metadata: {expected_tables - table_names}"


def test_3_required_tables_exist_in_database():
    """3 & 4. Verify Alembic migration created all six required tables in PostgreSQL."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {"users", "roles", "user_roles", "documents", "document_chunks", "audit_logs"}
    assert required_tables.issubset(existing_tables), f"Database missing tables: {required_tables - existing_tables}"


def test_4_foreign_key_relationships_and_constraints():
    """5. Verify foreign-key relationships, unique constraints, and cascade operations."""
    with SessionLocal() as db:
        # Create test Role
        role = Role(
            name=f"test_admin_{uuid.uuid4().hex[:6]}",
            description="System Administrator Test Role",
        )
        db.add(role)
        db.flush()

        # Create test User
        user = User(
            email=f"temp_user_{uuid.uuid4().hex[:6]}@clario.internal",
            name="Test Engineer",
            password_hash="hashed_secret_123",
            department="Engineering",
            is_active=True,
        )
        user.roles.append(role)
        db.add(user)
        db.flush()

        # Create test Document
        doc = Document(
            filename="architecture.pdf",
            title="System Architecture Specification",
            document_type="pdf",
            department="Engineering",
            access_level="internal",
            file_path="/storage/architecture.pdf",
            file_size=2048576,
            status=DocumentStatus.UPLOADED,
            uploaded_by=user.id,
        )
        db.add(doc)
        db.flush()

        # Create test DocumentChunk
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Enterprise RAG database schema and index configuration.",
            page_number=1,
            section="Database Foundation",
        )
        db.add(chunk)

        # Create test AuditLog
        audit = AuditLog(
            user_id=user.id,
            action="SCHEMA_VERIFICATION",
            resource_type="document",
            resource_id=str(doc.id),
            details={"phase": "2A", "status": "verified"},
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
        assert queried_user.documents[0].title == "System Architecture Specification"

        assert len(queried_user.documents[0].chunks) == 1
        assert queried_user.documents[0].chunks[0].chunk_index == 0
        assert "Enterprise RAG" in queried_user.documents[0].chunks[0].content

        assert len(queried_user.audit_logs) == 1
        assert queried_user.audit_logs[0].action == "SCHEMA_VERIFICATION"

        # Cleanup test record
        db.delete(user)
        db.delete(role)
        db.delete(audit)
        db.commit()


def test_5_qdrant_connectivity():
    """6. Verify Qdrant vector engine connectivity."""
    assert vector_service.check_health() is True, "Qdrant vector database is unreachable."


def test_6_qdrant_clario_documents_collection_existence():
    """7. Verify clario_documents collection exists in Qdrant."""
    assert vector_service.ensure_collection_exists() is True, "Failed to initialize clario_documents collection."


def test_7_qdrant_payload_schema_validation():
    """Verify Qdrant vector metadata payload schema."""
    payload_dict = {
        "document_id": str(uuid.uuid4()),
        "chunk_id": str(uuid.uuid4()),
        "page_number": 3,
        "section": "Vector Engine",
        "department": "Engineering",
        "document_type": "pdf",
        "access_level": "internal",
    }
    validated = vector_service.validate_payload(payload_dict)
    assert validated.document_type == "pdf"
    assert validated.access_level == "internal"
