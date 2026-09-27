import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class QdrantVectorPayload(BaseModel):
    """Schema representing the required payload metadata structure stored alongside vector embeddings in Qdrant."""
    
    document_id: str = Field(..., description="UUID string of parent document")
    chunk_id: str = Field(..., description="UUID string of specific document chunk")
    page_number: Optional[int] = Field(None, description="Page number where chunk originates")
    section: Optional[str] = Field(None, description="Section heading or document location")
    department: Optional[str] = Field(None, description="Department authorization scope")
    document_type: str = Field(..., description="File extension or document type (e.g. pdf, docx)")
    access_level: str = Field("internal", description="Document access classification level")

    model_config = ConfigDict(from_attributes=True)
