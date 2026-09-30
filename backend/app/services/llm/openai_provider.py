import time
import random
import logging
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMGenerationRequest,
    LLMGenerationResponse,
)

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class AuthenticationError(LLMProviderError):
    """Raised on non-retryable 401/403 provider authentication failures."""
    pass


class ContextLengthExceededError(LLMProviderError):
    """Raised when prompt exceeds model context window limit."""
    pass


class OpenAICompatibleProvider(BaseLLMProvider):
    """HTTP client provider for OpenAI-compatible Chat Completions endpoints (OpenAI, Azure, vLLM, Ollama).

    Includes bounded retries with jitter for transient errors, fail-fast handling on authentication/client errors,
    and strict log sanitization preventing secret leakage.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_API_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.model_name = model_name or settings.LLM_MODEL_NAME
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    def _build_payload(self, request: LLMGenerationRequest) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Synchronously execute chat completion with bounded retries."""
        payload = self._build_payload(request)
        headers = self._get_headers()
        url = f"{self.base_url}/chat/completions"

        last_err: Optional[Exception] = None
        t0 = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)

                # 1. Non-retryable Client Errors
                if resp.status_code in (401, 403):
                    logger.error(f"LLM Provider authentication failed (status {resp.status_code}).")
                    raise AuthenticationError("LLM provider authentication failed. Check API key configuration.")

                if resp.status_code == 400:
                    err_body = resp.text
                    if "context_length" in err_body.lower() or "maximum context" in err_body.lower():
                        logger.error("LLM Provider context length exceeded.")
                        raise ContextLengthExceededError("Prompt length exceeded maximum context limit.")
                    raise LLMProviderError(f"Bad request to LLM provider (status 400): {err_body[:200]}")

                if resp.status_code == 404:
                    raise LLMProviderError(f"LLM endpoint or model '{self.model_name}' not found (status 404).")

                # 2. Retryable Server / Rate Limit Errors
                if resp.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"Transient LLM provider error (status {resp.status_code}) on attempt {attempt + 1}/{self.max_retries + 1}."
                    )
                    last_err = LLMProviderError(f"Provider returned transient status {resp.status_code}")
                    if attempt < self.max_retries:
                        sleep_s = (2 ** attempt) * 0.5 + random.uniform(0.0, 0.2)
                        time.sleep(sleep_s)
                        continue
                    raise last_err

                resp.raise_for_status()
                data = resp.json()

                # 3. Parse completion response
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("LLM provider returned empty choices list.")

                message = choices[0].get("message", {})
                content = message.get("content", "")
                finish_reason = choices[0].get("finish_reason", "stop")

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                latency_ms = (time.perf_counter() - t0) * 1000.0

                return LLMGenerationResponse(
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    model_name=self.model_name,
                    finish_reason=finish_reason,
                    latency_ms=latency_ms,
                )

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning(
                    f"LLM provider network/timeout error on attempt {attempt + 1}/{self.max_retries + 1}: {type(net_err).__name__}"
                )
                last_err = net_err
                if attempt < self.max_retries:
                    sleep_s = (2 ** attempt) * 0.5 + random.uniform(0.0, 0.2)
                    time.sleep(sleep_s)
                    continue
                raise LLMProviderError(f"LLM provider request failed after {self.max_retries + 1} attempts: {net_err}") from net_err

        raise LLMProviderError(f"LLM generation failed: {last_err}")

    async def agenerate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Asynchronously execute chat completion with bounded retries."""
        payload = self._build_payload(request)
        headers = self._get_headers()
        url = f"{self.base_url}/chat/completions"

        last_err: Optional[Exception] = None
        t0 = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code in (401, 403):
                    raise AuthenticationError("LLM provider authentication failed. Check API key configuration.")

                if resp.status_code == 400:
                    err_body = resp.text
                    if "context_length" in err_body.lower() or "maximum context" in err_body.lower():
                        raise ContextLengthExceededError("Prompt length exceeded maximum context limit.")
                    raise LLMProviderError(f"Bad request to LLM provider (status 400): {err_body[:200]}")

                if resp.status_code in (429, 500, 502, 503, 504):
                    last_err = LLMProviderError(f"Provider returned transient status {resp.status_code}")
                    if attempt < self.max_retries:
                        import asyncio
                        sleep_s = (2 ** attempt) * 0.5 + random.uniform(0.0, 0.2)
                        await asyncio.sleep(sleep_s)
                        continue
                    raise last_err

                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("LLM provider returned empty choices list.")

                content = choices[0].get("message", {}).get("content", "")
                finish_reason = choices[0].get("finish_reason", "stop")
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                return LLMGenerationResponse(
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    model_name=self.model_name,
                    finish_reason=finish_reason,
                    latency_ms=latency_ms,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                last_err = net_err
                if attempt < self.max_retries:
                    import asyncio
                    sleep_s = (2 ** attempt) * 0.5 + random.uniform(0.0, 0.2)
                    await asyncio.sleep(sleep_s)
                    continue
                raise LLMProviderError(f"LLM provider request failed: {net_err}") from net_err

        raise LLMProviderError(f"LLM generation failed: {last_err}")
