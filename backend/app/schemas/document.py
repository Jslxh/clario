import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus


class DocumentChunkRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: uuid.UUID
    filename: str
    title: str
    document_type: str
    department: Optional[str] = None
    access_level: str
    file_path: str
    file_size: int
    status: DocumentStatus
    uploaded_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
