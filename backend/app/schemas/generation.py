from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field

from app.services.retrieval.models import SearchFilters, RetrievalMode


class SourceCitation(BaseModel):
    """Metadata for a document chunk cited in the generated answer."""
    source_tag: str = Field(..., description="Evidence reference tag in answer, e.g. '[Doc-1]'")
    chunk_id: str = Field(..., description="PostgreSQL UUID of the cited document chunk")
    document_id: str = Field(..., description="PostgreSQL UUID of the parent document")
    filename: str = Field(..., description="Source filename")
    page_number: Optional[int] = Field(None, description="Starting page number")
    end_page: Optional[int] = Field(None, description="Ending page number")
    section: Optional[str] = Field(None, description="Section heading")
    department: Optional[str] = Field(None, description="Department tag")
    access_level: str = Field(..., description="Document classification")
    relevance_score: float = Field(..., description="First or second-stage retrieval score")

    model_config = ConfigDict(from_attributes=True)


class GenerationRequest(BaseModel):
    """Request payload for enterprise question answering and LLM generation."""
    query: str = Field(..., min_length=1, description="User search / question text (non-empty)")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Max candidate chunks to retrieve for context construction")
    filters: Optional[SearchFilters] = Field(None, description="Optional search predicates (department, document_type, access_level, document_id)")
    mode: Optional[RetrievalMode] = Field(RetrievalMode.HYBRID, description="Retrieval mode: 'hybrid', 'semantic', 'bm25'")
    enable_rerank: Optional[bool] = Field(None, description="Whether to apply Cross-Encoder reranking")
    max_output_tokens: Optional[int] = Field(1024, ge=64, le=4096, description="Max tokens for LLM generation response")

    model_config = ConfigDict(from_attributes=True)


class GenerationResponse(BaseModel):
    """Response payload containing grounded answer and mapped source citations."""
    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Synthesized answer text containing inline source tags")
    citations: List[SourceCitation] = Field(..., description="List of source metadata objects for chunks actually provided in context")
    has_sufficient_context: bool = Field(..., description="Operational indicator of whether candidate chunks were available for context")
    model_name: str = Field(..., description="Model identifier used for generation")
    retrieval_mode: str = Field(..., description="Retrieval mode used ('hybrid', 'semantic', 'bm25')")
    latency_ms: float = Field(..., description="Total pipeline latency in milliseconds")
    token_usage: Dict[str, int] = Field(..., description="Token counts: prompt_tokens, completion_tokens, total_tokens")

    model_config = ConfigDict(from_attributes=True)


class ContextChunk(BaseModel):
    """Structured context evidence block packed for LLM prompt."""
    source_index: int = Field(..., description="1-based numerical index assigned to this evidence block: 1 for [Doc-1]")
    source_tag: str = Field(..., description="Formatted tag string '[Doc-1]'")
    chunk_id: str
    document_id: str
    filename: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    end_page: Optional[int] = None
    department: Optional[str] = None
    access_level: str
    content: str
    token_count: int
    score: float

    model_config = ConfigDict(from_attributes=True)


class BuiltContext(BaseModel):
    """Result of context construction packing and prompt assembly."""
    system_prompt: str
    user_prompt: str
    context_chunks: List[ContextChunk]
    total_context_tokens: int
    total_prompt_tokens: int
    dropped_chunk_count: int
    has_sufficient_context: bool

    model_config = ConfigDict(from_attributes=True)
