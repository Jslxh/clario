import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role, ROLE_USER
from app.models.conversation import Conversation, Message

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def users_and_tokens(db: Session):
    user_role = db.query(Role).filter(Role.name == ROLE_USER).first() or Role(name=ROLE_USER)
    db.add(user_role)
    db.flush()

    uid = uuid.uuid4().hex[:6]
    user_a = User(
        email=f"alice_{uid}@clario.enterprise",
        name="Alice",
        password_hash=hash_password("Pass123!"),
        department="Engineering",
        is_active=True,
    )
    user_a.roles.append(user_role)

    user_b = User(
        email=f"bob_{uid}@clario.enterprise",
        name="Bob",
        password_hash=hash_password("Pass123!"),
        department="HR",
        is_active=True,
    )
    user_b.roles.append(user_role)

    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    token_a = create_access_token(
        subject=str(user_a.id),
        email=user_a.email,
        roles=["user"],
        department=user_a.department,
    )
    token_b = create_access_token(
        subject=str(user_b.id),
        email=user_b.email,
        roles=["user"],
        department=user_b.department,
    )

    return {
        "user_a": user_a,
        "token_a": token_a,
        "user_b": user_b,
        "token_b": token_b,
    }


def test_1_conversation_creation_and_listing(users_and_tokens):
    headers_a = {"Authorization": f"Bearer {users_and_tokens['token_a']}"}
    headers_b = {"Authorization": f"Bearer {users_and_tokens['token_b']}"}

    # Alice creates a conversation
    resp = client.post(
        "/api/v1/conversations",
        headers=headers_a,
        json={"title": "Alice's Project Discussion"},
    )
    assert resp.status_code == 201
    conv_data = resp.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Alice's Project Discussion"

    # Alice lists conversations
    list_a = client.get("/api/v1/conversations", headers=headers_a)
    assert list_a.status_code == 200
    assert any(c["id"] == conv_id for c in list_a.json())

    # Bob lists conversations - must be empty (isolated)
    list_b = client.get("/api/v1/conversations", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(c["id"] == conv_id for c in list_b.json())


def test_2_cross_user_access_denial(users_and_tokens):
    headers_a = {"Authorization": f"Bearer {users_and_tokens['token_a']}"}
    headers_b = {"Authorization": f"Bearer {users_and_tokens['token_b']}"}

    # Alice creates a conversation
    resp = client.post(
        "/api/v1/conversations",
        headers=headers_a,
        json={"title": "Confidential Engineering Chat"},
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    # Bob attempts to get Alice's conversation -> 403 Forbidden
    get_resp = client.get(f"/api/v1/conversations/{conv_id}", headers=headers_b)
    assert get_resp.status_code == 403

    # Bob attempts to post message to Alice's conversation -> 403 Forbidden
    post_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers_b,
        json={"content": "Unauthorized intrusion attempt"},
    )
    assert post_resp.status_code == 403

    # Bob attempts to delete Alice's conversation -> 403 Forbidden
    del_resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=headers_b)
    assert del_resp.status_code == 403


def test_3_multi_turn_message_and_followup_rag_generation(users_and_tokens):
    headers_a = {"Authorization": f"Bearer {users_and_tokens['token_a']}"}

    # Alice creates conversation
    create_resp = client.post(
        "/api/v1/conversations",
        headers=headers_a,
        json={"title": "Q&A Session"},
    )
    conv_id = create_resp.json()["id"]

    # Turn 1: Post question
    turn_1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "What is the company leave policy?", "verify": True},
    )
    assert turn_1.status_code == 200
    turn_1_data = turn_1.json()
    assert turn_1_data["user_message"]["content"] == "What is the company leave policy?"
    assert turn_1_data["assistant_message"]["role"] == "assistant"
    assert "answer" in turn_1_data["generation"]

    # Retrieve conversation history
    get_conv = client.get(f"/api/v1/conversations/{conv_id}", headers=headers_a)
    assert get_conv.status_code == 200
    messages = get_conv.json()["messages"]
    assert len(messages) == 2  # 1 user + 1 assistant
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # Alice deletes her conversation
    del_resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=headers_a)
    assert del_resp.status_code == 204
