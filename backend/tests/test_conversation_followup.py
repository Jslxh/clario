import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_USER
from app.models.conversation import Conversation, Message
from app.services.generation.service import generation_service
from app.services.context.builder import context_builder
from app.services.retrieval.models import RetrievalResult

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def conv_user(db: Session):
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add(user_role)
    db.flush()

    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"conv_{uid}@clario.enterprise",
        name="Conv Tester",
        password_hash=hash_password("Pass123!"),
        department="Engineering",
        is_active=True,
    )
    user.roles.append(user_role)
    db.add(user)
    db.commit()

    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        roles=["user"],
        department=user.department,
    )
    return {"user": user, "token": token}


def test_contextualize_query_heuristics():
    """Verify that follow-up queries with pronouns/ellipsis are contextualized."""
    # 1. Empty history -> remains identical
    assert generation_service.contextualize_query("What is the refund policy?", []) == "What is the refund policy?"

    # 2. Standalone question with history -> remains unchanged
    history = [
        {"role": "user", "content": "Tell me about project Apollo."},
        {"role": "assistant", "content": "Project Apollo is our new cloud platform."},
    ]
    query_standalone = "What is the capital of France?"
    assert generation_service.contextualize_query(query_standalone, history) == query_standalone

    # 3. Follow-up query with pronoun -> contextualized
    followup_1 = "How many weeks does it offer?"
    contextualized_1 = generation_service.contextualize_query(followup_1, history)
    assert "Apollo" in contextualized_1 or "cloud platform" in contextualized_1
    assert "How many weeks does it offer?" in contextualized_1

    # 4. Elliptical follow-up
    followup_2 = "What about pricing?"
    contextualized_2 = generation_service.contextualize_query(followup_2, history)
    assert "Apollo" in contextualized_2 or "cloud platform" in contextualized_2


def test_context_builder_includes_conversation_history():
    """Verify context_builder includes <conversation_history> when history is present."""
    candidates = [
        RetrievalResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            filename="handbook.pdf",
            document_type="pdf",
            content="Standard leave is 20 days per year.",
            score=0.9,
            department="Engineering",
            access_level="internal",
        )
    ]
    history = [
        {"role": "user", "content": "Hello, can I ask a policy question?"},
        {"role": "assistant", "content": "Yes, please ask away."},
    ]

    built = context_builder.build_context(
        query="What is standard leave?",
        candidates=candidates,
        history=history,
    )
    assert "<conversation_history>" in built.user_prompt
    assert "Hello, can I ask a policy question?" in built.user_prompt
    assert "Yes, please ask away." in built.user_prompt
    assert "<enterprise_context>" in built.user_prompt
    assert "What is standard leave?" in built.user_prompt


def test_multi_turn_followup_rag_retrieval(conv_user):
    """Verify follow-up question in conversation uses context and preserves citations."""
    headers = {"Authorization": f"Bearer {conv_user['token']}"}

    # Create conversation
    create_res = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Multi-turn RAG Test"},
    )
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # Turn 1
    t1_res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "What is the security onboarding procedure?", "verify": False},
    )
    assert t1_res.status_code == 200

    # Turn 2: Follow-up question relying on previous turn context
    t2_res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "How long does it take to complete?", "verify": False},
    )
    assert t2_res.status_code == 200
    t2_data = t2_res.json()
    assert t2_data["user_message"]["content"] == "How long does it take to complete?"
    assert t2_data["assistant_message"]["role"] == "assistant"
    assert "answer" in t2_data["generation"]
