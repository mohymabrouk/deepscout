from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import TOKEN_BUDGET_EXCEEDED, DomainError
from app.research.models import LLMResponse


def estimate_tokens(value: str) -> int:
    """Conservative provider-independent estimate used before network calls."""
    return max(1, (len(value) + 3) // 4)


@dataclass
class RunBudget:
    max_llm_calls: int
    max_input_tokens: int
    max_output_tokens: int
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def reserve_call(self, estimated_input: int, requested_output: int) -> tuple[int, int]:
        if self.llm_calls + 1 > self.max_llm_calls:
            raise DomainError(
                TOKEN_BUDGET_EXCEEDED, "The research run reached its model-call budget.", 429
            )
        if self.input_tokens + estimated_input > self.max_input_tokens:
            raise DomainError(
                TOKEN_BUDGET_EXCEEDED, "The research context exceeds the input token budget.", 429
            )
        if self.output_tokens + requested_output > self.max_output_tokens:
            raise DomainError(
                TOKEN_BUDGET_EXCEEDED, "The research output exceeds the token budget.", 429
            )
        self.llm_calls += 1
        self.input_tokens += estimated_input
        self.output_tokens += requested_output
        return estimated_input, requested_output

    def reconcile(self, reservation: tuple[int, int], response: LLMResponse) -> None:
        estimated_input, requested_output = reservation
        actual_input = max(0, response.usage.input_tokens)
        actual_output = max(0, response.usage.output_tokens)
        self.input_tokens += actual_input - estimated_input
        self.output_tokens += actual_output - requested_output
        if self.input_tokens > self.max_input_tokens or self.output_tokens > self.max_output_tokens:
            raise DomainError(
                TOKEN_BUDGET_EXCEEDED, "The provider response exceeded the token budget.", 429
            )

    def usage(self) -> tuple[int, int, int]:
        return self.input_tokens, self.output_tokens, self.llm_calls
