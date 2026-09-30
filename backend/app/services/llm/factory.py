import logging
from typing import Optional

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """Factory creating the configured LLM provider instance."""
    resolved_type = (provider_type or settings.LLM_PROVIDER or "mock").lower().strip()

    if resolved_type in ("openai", "azure", "vllm", "ollama"):
        logger.info(f"Instantiating OpenAI-compatible LLM provider ({resolved_type})...")
        return OpenAICompatibleProvider()

    # Default: deterministic offline Mock provider
    logger.info("Instantiating deterministic offline MockLLMProvider...")
    return MockLLMProvider()


llm_provider = get_llm_provider()
