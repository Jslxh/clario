import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class NormalizedChunk(BaseModel):
    """Normalized internal representation of a document chunk before/after database persistence."""

    document_id: str = Field(..., description="UUID string of parent document")
    chunk_id: Optional[str] = Field(None, description="UUID string of chunk")
    chunk_index: int = Field(..., description="0-indexed sequence position of chunk")
    content: str = Field(..., description="Text content of the chunk")
    section: Optional[str] = Field(None, description="Section heading context")
    start_page: Optional[int] = Field(None, description="Starting page number (None for TXT)")
    end_page: Optional[int] = Field(None, description="Ending page number (None for TXT)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk lineage and token metadata")

    model_config = ConfigDict(from_attributes=True)
