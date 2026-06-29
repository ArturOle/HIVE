
from typing import Any, TypedDict
from pydantic import BaseModel, Field, field_validator


class WriterState(TypedDict, total=False):
    """LangGraph state for writer pipeline."""

    text: str
    environment_hint: str
    extractions: list[dict[str, str]]  # Multiple extractions per text
    reflections: list[dict[str, Any]]  # Multiple reflections
    embeddings_list: list[dict[str, list[float]]]  # Multiple embedding sets
    persisted: list[dict[str, Any]]  # Multiple persisted entries
    errors: list[str]


class WriterExtraction(BaseModel):
    """Validated extraction contract for graph persistence."""

    environment: str
    problem: str
    solution: str
    mechanism: str
    result: str

    @field_validator("environment", "problem", "solution", "mechanism", "result", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> str:
        """Convert list or other types to string for all fields."""
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        if isinstance(v, str):
            return v
        return str(v)


class WriterReflection(BaseModel):
    """Validated reflection contract for quality metadata."""

    grade: float = Field(ge=0.0, le=5.0)
    reasoning: str
    key_lesson: str
    risk_factors: str

    @field_validator("reasoning", "key_lesson", "risk_factors", mode="before")
    @classmethod
    def coerce_string_fields(cls, v: Any) -> str:
        """Convert list or other types to string for all string fields."""
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        if isinstance(v, str):
            return v
        return str(v)