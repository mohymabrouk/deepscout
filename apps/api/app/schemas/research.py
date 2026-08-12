from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RunStatus = Literal[
    "pending",
    "planning",
    "searching",
    "fetching",
    "selecting",
    "synthesizing",
    "verifying",
    "completed",
    "failed",
    "limited",
]


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1500)
    mode: Literal["standard"] = "standard"

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 10:
            raise ValueError("Question must be at least 10 characters.")
        if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
            raise ValueError("Question contains an unsupported control character.")
        return value


class ResearchAccepted(BaseModel):
    run_id: str
    status: Literal["pending"]
    events_url: str


QualityLabel = Literal["high", "medium", "low"]


class SourceQuality(BaseModel):
    score: float = Field(ge=0, le=1)
    label: QualityLabel
    reasons: list[str] = Field(default_factory=list, max_length=5)


class Source(BaseModel):
    citation_id: int
    title: str
    url: str
    domain: str
    retrieved_at: datetime
    quality: SourceQuality = Field(
        default_factory=lambda: SourceQuality(
            score=0.5, label="medium", reasons=["Quality signals were not available."]
        )
    )


class ReportParagraph(BaseModel):
    text: str
    citations: list[int] = Field(default_factory=list)


class ReportSection(BaseModel):
    heading: str
    paragraphs: list[ReportParagraph]


class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    limitations: list[str] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    llm_calls: int


class ResearchResult(BaseModel):
    id: str
    status: RunStatus
    question: str | None = None
    report: ResearchReport | None = None
    sources: list[Source] = Field(default_factory=list)
    usage: Usage | None = None
    error_code: str | None = None


class RunSummary(BaseModel):
    id: str
    status: RunStatus
    question: str
    title: str | None = None
    source_count: int = 0
    created_at: datetime
    completed_at: datetime | None = None


class RunListResponse(BaseModel):
    items: list[RunSummary]
    next_cursor: str | None = None


class UsageResponse(BaseModel):
    period: Literal["day"]
    runs_used: int
    runs_limit: int
    input_tokens_used: int
    input_tokens_limit: int
    resets_at: datetime
