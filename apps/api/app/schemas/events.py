from typing import Any, Literal

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    event: Literal["stage", "complete", "error"]
    stage: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

