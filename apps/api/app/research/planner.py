from __future__ import annotations

import json

from app.core.errors import INSUFFICIENT_SOURCES, DomainError
from app.research.budget import RunBudget, estimate_tokens
from app.research.models import LLMProvider, LLMRequest, PlannerResult


class Planner:
    def __init__(self, provider: LLMProvider, budget: RunBudget, max_queries: int) -> None:
        self.provider, self.budget, self.max_queries = provider, budget, max_queries

    async def plan(self, question: str) -> PlannerResult:
        request = LLMRequest(
            purpose="planner",
            messages=[
                {
                    "role": "system",
                    "content": "Return only JSON with queries, intent, and must_cover. Do not answer.",
                },
                {"role": "user", "content": question},
            ],
            max_output_tokens=min(400, self.budget.max_output_tokens),
            temperature=0.2,
        )
        serialized = json.dumps(request.messages)
        reservation = self.budget.reserve_call(
            estimate_tokens(serialized), request.max_output_tokens
        )
        response = await self.provider.complete(request)
        self.budget.reconcile(reservation, response)
        try:
            payload = json.loads(response.content)
            queries = [str(query).strip() for query in payload["queries"] if str(query).strip()]
            intent = str(payload.get("intent", "other"))
            must_cover = [
                str(item).strip() for item in payload.get("must_cover", []) if str(item).strip()
            ]
        except (ValueError, KeyError, TypeError) as exc:
            raise DomainError(
                INSUFFICIENT_SOURCES, "The research planner returned an invalid plan.", 502
            ) from exc
        queries = list(dict.fromkeys(queries))[: self.max_queries]
        if not queries:
            raise DomainError(
                INSUFFICIENT_SOURCES, "The research planner returned no usable queries.", 502
            )
        return PlannerResult(queries, intent, must_cover)
