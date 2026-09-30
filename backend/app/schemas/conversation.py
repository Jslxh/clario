import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation import GenerationResponse


class MessageBase(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="User follow-up question / message")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Max candidate chunks for RAG retrieval")
    verify: Optional[bool] = Field(None, description="Explicitly enable/disable grounding verification")


class MessageRead(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    verification_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", description="Title for conversation session")


class ConversationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationMessageResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
    generation: GenerationResponse

    model_config = ConfigDict(from_attributes=True)
