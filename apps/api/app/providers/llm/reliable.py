from __future__ import annotations

import asyncio
import json

from app.core.errors import PROVIDER_RATE_LIMIT, PROVIDER_UNAVAILABLE, DomainError
from app.research.budget import RunBudget, estimate_tokens
from app.research.models import LLMProvider, LLMRequest, LLMResponse

TRANSIENT_ERRORS = {PROVIDER_RATE_LIMIT, PROVIDER_UNAVAILABLE}


class ReliableLLMProvider:
    """Retries only transient failures and falls back without exceeding RunBudget."""

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None,
        max_retries: int,
        backoff_seconds: float,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    async def complete(self, request: LLMRequest, budget: RunBudget | None = None) -> LLMResponse:
        last_error: DomainError | None = None
        providers = [self.primary] + ([self.fallback] if self.fallback is not None else [])
        for provider_index, provider in enumerate(providers):
            for attempt in range(self.max_retries + 1):
                reservation = None
                if budget is not None:
                    reservation = budget.reserve_call(
                        estimate_tokens(json.dumps(request.messages)), request.max_output_tokens
                    )
                try:
                    response = await provider.complete(request)
                except DomainError as exc:
                    if budget is not None and reservation is not None:
                        budget.release_output_reservation(reservation)
                    if exc.code not in TRANSIENT_ERRORS:
                        raise
                    last_error = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.backoff_seconds * (2**attempt))
                        continue
                    if provider_index + 1 < len(providers):
                        break
                else:
                    if budget is not None and reservation is not None:
                        budget.reconcile(reservation, response)
                    return response
        if last_error is not None:
            raise last_error
        raise DomainError(PROVIDER_UNAVAILABLE, "The inference provider is unavailable.", 503)

