from __future__ import annotations

import json
import re

from app.research.models import LLMRequest, LLMResponse, LLMUsage


class DemoLLMProvider:
    """Deterministic provider for local development and tests; never calls the network."""

    provider = "demo"
    model = "demo-v1"

    async def complete(self, request: LLMRequest, budget=None) -> LLMResponse:
        if request.purpose == "planner":
            question = request.messages[-1]["content"]
            words = [word for word in re.findall(r"[\w-]+", question.lower()) if len(word) > 3]
            core = " ".join(words[:8]) or "research topic"
            payload = {
                "queries": [
                    core,
                    f"{core} official documentation",
                    f"{core} comparison limitations",
                ],
                "intent": "comparison" if "compare" in question.lower() else "explanation",
                "must_cover": ["key findings", "limitations", "practical considerations"],
            }
        else:
            user_content = request.messages[-1]["content"]
            ids = [int(value) for value in re.findall(r'SOURCE id=["\']?(\d+)', user_content)]
            citations = ids[:3]
            title = "Research brief"
            if request.purpose == "repair":
                payload = json.loads(user_content.split("\n", 1)[-1])
                for section in payload.get("sections", []):
                    for paragraph in section.get("paragraphs", []):
                        paragraph["citations"] = [
                            citation
                            for citation in paragraph.get("citations", [])
                            if citation in ids
                        ]
                payload.setdefault("limitations", []).append(
                    "Citations were normalized against fetched sources."
                )
            else:
                evidence = re.findall(r"<EVIDENCE>(.*?)</EVIDENCE>", user_content, flags=re.DOTALL)
                lead_evidence = " ".join(evidence[0].split())[:360] if evidence else "No evidence excerpt was available."
                payload = {
                    "title": title,
                    "executive_summary": "The available sources provide a bounded starting point grounded in the retrieved evidence.",
                    "sections": [
                        {
                            "heading": "Key findings",
                            "paragraphs": [
                                {
                                    "text": f"The retrieved evidence says: {lead_evidence} Weigh it by relevance, source quality, and stated limitations.",
                                    "citations": citations,
                                }
                            ],
                        }
                    ],
                    "limitations": ["This local demo uses deterministic provider output."],
                }
        content = json.dumps(payload)
        return LLMResponse(
            content=content,
            usage=LLMUsage(
                input_tokens=max(1, len(json.dumps(request.messages)) // 4),
                output_tokens=max(1, len(content) // 4),
            ),
            provider=self.provider,
            model=self.model,
        )
