import pytest
from app.core.errors import DomainError
from app.research.budget import RunBudget, estimate_tokens
from app.research.models import LLMResponse, LLMUsage


def test_estimate_tokens_is_conservative_and_positive():
    assert estimate_tokens("") == 1
    assert estimate_tokens("1234") == 1
    assert estimate_tokens("12345") == 2


def test_budget_rejects_calls_over_total_output_allowance():
    budget = RunBudget(max_llm_calls=3, max_input_tokens=1000, max_output_tokens=500)
    budget.reserve_call(10, 400)
    with pytest.raises(DomainError) as error:
        budget.reserve_call(10, 101)
    assert error.value.code == "TOKEN_BUDGET_EXCEEDED"


def test_budget_reconciles_provider_usage():
    budget = RunBudget(max_llm_calls=3, max_input_tokens=1000, max_output_tokens=500)
    reservation = budget.reserve_call(100, 200)
    budget.reconcile(
        reservation,
        LLMResponse("{}", LLMUsage(input_tokens=20, output_tokens=30), "test", "test"),
    )
    assert budget.usage() == (20, 30, 1)
