import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.services.llm.base import LLMGenerationRequest
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import (
    OpenAICompatibleProvider,
    AuthenticationError,
    ContextLengthExceededError,
    LLMProviderError,
)
from app.services.llm.factory import get_llm_provider


def test_1_mock_provider_deterministic_synthesis():
    """1. Verify MockLLMProvider parses XML evidence blocks and outputs formatted citation tags."""
    provider = MockLLMProvider()

    user_prompt = (
        "<enterprise_context>\n"
        '<document index="1" tag="[Doc-1]" source="leave_policy.pdf" pages="1" section="Vacation">\n'
        "Employees receive 18 days of paid annual vacation leave.\n"
        "</document>\n"
        '<document index="2" tag="[Doc-2]" source="security.pdf" pages="3" section="MFA">\n'
        "Production access requires FIDO2 hardware tokens.\n"
        "</document>\n"
        "</enterprise_context>\n\n"
        "User Question: What is the vacation policy?"
    )

    req = LLMGenerationRequest(
        system_prompt="System instructions.",
        user_prompt=user_prompt,
    )

    resp = provider.generate(req)
    assert resp.content != ""
    assert "[Doc-1]" in resp.content
    assert "[Doc-2]" in resp.content
    assert "leave_policy.pdf" in resp.content
    assert resp.finish_reason == "stop"
    assert resp.total_tokens > 0


def test_2_mock_provider_empty_context_abstention():
    """2. Verify MockLLMProvider outputs abstention message when no evidence blocks are provided."""
    provider = MockLLMProvider()

    req = LLMGenerationRequest(
        system_prompt="System instructions.",
        user_prompt="<enterprise_context>\n</enterprise_context>\n\nUser Question: Who is CEO?",
    )

    resp = provider.generate(req)
    assert "cannot find sufficient information" in resp.content.lower()


def test_3_mock_provider_simulated_failure():
    """3. Verify MockLLMProvider simulated failure hook."""
    provider = MockLLMProvider(simulate_failure=RuntimeError("Simulated LLM network drop"))

    req = LLMGenerationRequest(
        system_prompt="System instructions.",
        user_prompt="User Question: Test query",
    )

    with pytest.raises(RuntimeError, match="Simulated LLM network drop"):
        provider.generate(req)


def test_4_openai_provider_fail_fast_on_401_auth_error():
    """4. Verify OpenAICompatibleProvider fails fast on 401/403 without burning retries."""
    provider = OpenAICompatibleProvider(api_key="invalid-key", max_retries=2)

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": {"message": "Incorrect API key provided"}}'

    req = LLMGenerationRequest(
        system_prompt="System",
        user_prompt="User",
    )

    with patch.object(httpx.Client, "post", return_value=mock_resp) as mock_post:
        with pytest.raises(AuthenticationError, match="authentication failed"):
            provider.generate(req)
        # Verify it did not retry on 401
        assert mock_post.call_count == 1


def test_5_openai_provider_context_length_error_classification():
    """5. Verify OpenAICompatibleProvider classifies context length 400 error correctly."""
    provider = OpenAICompatibleProvider(api_key="test-key", max_retries=0)

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": {"message": "This model maximum context length is 8192 tokens. Please reduce the length of the messages."}}'

    req = LLMGenerationRequest(system_prompt="Sys", user_prompt="User")

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        with pytest.raises(ContextLengthExceededError):
            provider.generate(req)


def test_6_openai_provider_retries_transient_429():
    """6. Verify OpenAICompatibleProvider retries transient 429 rate limit."""
    provider = OpenAICompatibleProvider(api_key="test-key", max_retries=2)

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate limit exceeded"

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "choices": [{"message": {"content": "Success response."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    req = LLMGenerationRequest(system_prompt="Sys", user_prompt="User")

    with patch("time.sleep", return_value=None):
        with patch.object(httpx.Client, "post", side_effect=[mock_429, mock_200]) as mock_post:
            resp = provider.generate(req)
            assert resp.content == "Success response."
            assert mock_post.call_count == 2


def test_7_factory_resolution():
    """7. Verify get_llm_provider returns MockLLMProvider by default and OpenAIProvider when configured."""
    p_mock = get_llm_provider("mock")
    assert isinstance(p_mock, MockLLMProvider)

    p_openai = get_llm_provider("openai")
    assert isinstance(p_openai, OpenAICompatibleProvider)
