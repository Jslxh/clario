import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
    ConversationMessageResponse,
)
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new multi-turn conversation session."""
    conv = conversation_service.create_conversation(
        db=db,
        user_id=current_user.id,
        title=req.title,
    )
    return ConversationRead.model_validate(conv)


@router.get("", response_model=List[ConversationRead], status_code=status.HTTP_200_OK)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all conversations owned by the authenticated user."""
    convs = conversation_service.list_conversations(db=db, user_id=current_user.id)
    return [ConversationRead.model_validate(c) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationRead, status_code=status.HTTP_200_OK)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full conversation and message history for an owned conversation."""
    conv = conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return ConversationRead.model_validate(conv)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation session owned by the authenticated user."""
    conversation_service.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return None


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_200_OK,
)
def post_conversation_message(
    conversation_id: uuid.UUID,
    req: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post user message, trigger grounded RAG question answering with user permissions, and save assistant turn."""
    user_msg, assistant_msg, gen_resp = conversation_service.post_message(
        db=db,
        conversation_id=conversation_id,
        user=current_user,
        req=req,
    )
    return ConversationMessageResponse(
        user_message=MessageRead.model_validate(user_msg),
        assistant_message=MessageRead.model_validate(assistant_msg),
        generation=gen_resp,
    )
