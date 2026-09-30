import uuid
import logging
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.conversation import MessageCreate
from app.schemas.generation import GenerationResponse
from app.services.generation import generation_service

logger = logging.getLogger(__name__)


class ConversationService:
    """Service handling multi-turn conversation sessions, ownership isolation, and follow-up RAG generation."""

    def create_conversation(
        self,
        db: Session,
        user_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation session owned by user_id."""
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title.strip() if title and title.strip() else "New Conversation",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    def list_conversations(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> List[Conversation]:
        """List all conversation sessions belonging strictly to user_id."""
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def get_conversation(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Conversation:
        """Retrieve conversation by ID enforcing strict user ownership."""
        conv = (
            db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        if conv.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this conversation.",
            )
        return conv

    def delete_conversation(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete conversation by ID enforcing strict user ownership."""
        conv = self.get_conversation(db=db, conversation_id=conversation_id, user_id=user_id)
        db.delete(conv)
        db.commit()
        return True

    def post_message(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user: User,
        req: MessageCreate,
    ) -> Tuple[Message, Message, GenerationResponse]:
        """Post a user message to conversation, execute RAG generation with user authorization, and persist turns."""
        conv = self.get_conversation(db=db, conversation_id=conversation_id, user_id=user.id)

        # 1. Create and persist user message turn
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content=req.content.strip(),
        )
        db.add(user_msg)
        db.flush()

        # 2. Execute RAG question answering pipeline enforcing user authorization
        # We pass user to guarantee document access boundaries are respected
        gen_resp = generation_service.answer_query(
            db=db,
            query=req.content.strip(),
            top_k=req.top_k,
            verify=req.verify,
            user=user,
        )

        verification_status_str = None
        if gen_resp.verification:
            verification_status_str = gen_resp.verification.status.value

        # 3. Create and persist assistant message turn
        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content=gen_resp.answer,
            verification_status=verification_status_str,
        )
        db.add(assistant_msg)
        
        # Update conversation title if first turn
        if len(conv.messages) <= 2 and conv.title == "New Conversation":
            first_words = " ".join(req.content.strip().split()[:6])
            conv.title = first_words[:60]

        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return user_msg, assistant_msg, gen_resp


conversation_service = ConversationService()
