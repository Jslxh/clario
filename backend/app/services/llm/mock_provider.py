import re
import time
from typing import Optional, List

from app.core.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMGenerationRequest,
    LLMGenerationResponse,
)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, offline, context-aware mock provider for CI testing and hermetic development.

    Extracts facts from supplied <document> XML tags in the prompt and synthesizes a formatted answer
    with valid citations. Supports error-simulation hooks for retry and failure testing.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        simulate_failure: Optional[Exception] = None,
        simulate_unknown_tag: bool = False,
    ):
        self.model_name = model_name or settings.LLM_MODEL_NAME
        self.simulate_failure = simulate_failure
        self.simulate_unknown_tag = simulate_unknown_tag

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Synchronously generate deterministic completion."""
        t0 = time.perf_counter()

        # Check simulated failure hook
        if self.simulate_failure is not None:
            raise self.simulate_failure

        user_prompt = request.user_prompt

        # Extract user query
        query_match = re.search(r"User Question:\s*(.+)$", user_prompt, re.DOTALL)
        query_text = query_match.group(1).strip() if query_match else ""

        # Extract evidence blocks from <enterprise_context>
        doc_pattern = re.compile(
            r'<document index="(\d+)" tag="(\[Doc-\d+\])" source="([^"]+)"[^>]*>\n(.*?)\n</document>',
            re.DOTALL,
        )
        matches = doc_pattern.findall(user_prompt)

        if not matches:
            content = "I cannot find sufficient information in the provided documentation to answer your question."
        else:
            # Construct deterministic answer combining evidence
            statements = []
            for idx, tag, source, chunk_text in matches:
                # Take first coherent sentence or phrase from chunk
                clean_chunk = " ".join(chunk_text.strip().split())
                first_period = clean_chunk.find(".")
                snippet = clean_chunk[:first_period + 1] if first_period > 10 else clean_chunk[:120]
                statements.append(f"Based on {source}, {snippet} {tag}")

            content = " ".join(statements)
            if self.simulate_unknown_tag:
                content += " Additional unverified data [Doc-99]."

        latency_ms = (time.perf_counter() - t0) * 1000.0

        prompt_tokens = int(len(request.system_prompt + request.user_prompt) / 3.5)
        completion_tokens = max(10, int(len(content) / 3.5))

        return LLMGenerationResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model_name=self.model_name,
            finish_reason="stop",
            latency_ms=latency_ms,
        )

    async def agenerate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Asynchronously generate deterministic completion."""
        return self.generate(request)
