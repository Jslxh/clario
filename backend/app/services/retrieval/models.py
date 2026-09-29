from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SearchFilters(BaseModel):
    """Optional metadata filter criteria for candidate chunk retrieval.
    
    Note: These filters are technical search predicates applied at the vector index level.
    They do NOT constitute an authorization or RBAC boundary. Security boundaries will be
    established in later security/authorization phases.
    """
    department: Optional[str] = Field(None, description="Filter by target department")
    document_type: Optional[str] = Field(None, description="Filter by document format extension (pdf, docx, txt)")
    access_level: Optional[str] = Field(None, description="Filter by document access classification level")
    document_id: Optional[str] = Field(None, description="Filter by parent document UUID")

    model_config = ConfigDict(from_attributes=True)


class RetrievalResult(BaseModel):
    """Structured search result for a single retrieved document chunk.
    
    The canonical content is hydrated directly from PostgreSQL, while score represents
    vector similarity from Qdrant.
    """
    chunk_id: str = Field(..., description="Unique UUID string of the document chunk")
    document_id: str = Field(..., description="Unique UUID string of the parent document")
    score: float = Field(..., description="Cosine vector similarity score (not a probability or confidence percentage)")
    content: str = Field(..., description="Canonical chunk text content retrieved from PostgreSQL")
    page_number: Optional[int] = Field(None, description="Starting page number within original document")
    end_page: Optional[int] = Field(None, description="Ending page number within original document")
    section: Optional[str] = Field(None, description="Header or section title within original document")
    filename: str = Field(..., description="Original filename of parent document")
    document_type: str = Field(..., description="Format/type of parent document")
    department: Optional[str] = Field(None, description="Department metadata tag")
    access_level: str = Field(..., description="Access level metadata tag")

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    """Incoming request payload for semantic document search."""
    query: str = Field(..., description="Search query text (must not be empty or whitespace-only)")
    top_k: Optional[int] = Field(5, description="Number of top candidate chunks to return (1-100)")
    filters: Optional[SearchFilters] = Field(None, description="Optional metadata filter criteria")

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Response model for semantic search API."""
    query: str = Field(..., description="Cleaned search query text")
    total_results: int = Field(..., description="Total count of retrieved candidate chunks")
    results: List[RetrievalResult] = Field(..., description="List of retrieved candidate chunks ordered by vector similarity score")

    model_config = ConfigDict(from_attributes=True)
