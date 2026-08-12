import json
from pathlib import Path

from evals.run_eval import load_cases


def test_curated_dataset_has_thirty_cases_and_required_categories():
    path = Path(__file__).parents[1] / "cases.jsonl"
    cases = load_cases(path)
    assert 30 <= len(cases) <= 50
    assert len({case.id for case in cases}) == len(cases)
    categories = {case.category for case in cases}
    assert {
        "technical comparison",
        "technical explanation",
        "market landscape",
        "fact verification",
        "recency-sensitive research",
        "ambiguous question",
        "insufficient evidence",
        "provider/search failure simulation",
    } <= categories
    for line in path.read_text().splitlines():
        payload = json.loads(line)
        assert payload["question"].strip()
        assert payload["must_include_concepts"]
