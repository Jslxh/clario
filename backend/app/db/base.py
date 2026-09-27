# Import Base and all models for Alembic migration metadata resolution
from app.core.database import Base
from app.models import (
    User,
    Role,
    user_roles,
    Document,
    DocumentChunk,
    DocumentStatus,
    AuditLog,
)

__all__ = [
    "Base",
    "User",
    "Role",
    "user_roles",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "AuditLog",
]
