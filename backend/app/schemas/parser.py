from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ParsedPage(BaseModel):
    """Normalized representation of a single document page or text block."""
    
    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted text content for this page/unit")
    sections: List[str] = Field(default_factory=list, description="Section headings extracted on this page")

    model_config = ConfigDict(from_attributes=True)


class ParsedDocument(BaseModel):
    """Normalized internal representation of parsed document content across all units/pages."""

    document_id: str = Field(..., description="Unique document UUID string")
    filename: str = Field(..., description="Original or sanitized source filename")
    document_type: str = Field(..., description="Document type (pdf, docx, txt)")
    has_usable_text: bool = Field(True, description="True if usable text was successfully extracted")
    total_pages: int = Field(..., description="Total count of pages or content units")
    pages: List[ParsedPage] = Field(default_factory=list, description="List of page objects")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document-level metadata")

    model_config = ConfigDict(from_attributes=True)
