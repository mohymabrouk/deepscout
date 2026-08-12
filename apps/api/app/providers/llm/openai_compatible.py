from __future__ import annotations

import httpx

from app.core.errors import PROVIDER_RATE_LIMIT, PROVIDER_UNAVAILABLE, DomainError
from app.research.models import LLMRequest, LLMResponse, LLMUsage


class OpenAICompatibleProvider:
    """Adapter for providers exposing the OpenAI chat-completions shape."""

    def __init__(
        self, name: str, api_key: str, model: str, base_url: str, timeout: float = 25.0
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=body,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise DomainError(
                PROVIDER_UNAVAILABLE, "The inference provider is unavailable.", 503
            ) from exc
        if response.status_code == 429:
            raise DomainError(PROVIDER_RATE_LIMIT, "The inference provider is rate limited.", 503)
        if response.status_code >= 500:
            raise DomainError(PROVIDER_UNAVAILABLE, "The inference provider is unavailable.", 503)
        if response.status_code >= 400:
            raise DomainError(
                PROVIDER_UNAVAILABLE, "The inference provider rejected the request.", 503
            )
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise DomainError(
                PROVIDER_UNAVAILABLE, "The inference provider returned malformed data.", 503
            ) from exc
        return LLMResponse(
            content=content,
            usage=LLMUsage(
                int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
            ),
            provider=self.name,
            model=self.model,
        )
