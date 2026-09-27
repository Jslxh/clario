import uuid
import enum
from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Text, BigInteger, Integer, ForeignKey, Enum as SQLEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.base import TimestampMixin


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    access_level: Mapped[str] = mapped_column(
        String(50),
        default="internal",
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(
            DocumentStatus,
            name="document_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    uploader: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="documents",
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    section: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped[Document] = relationship(
        "Document",
        back_populates="chunks",
    )
