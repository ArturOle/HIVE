"""Writer agent LangGraph workflow for storing knowledge in Neo4j."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator

from ai.prompts import (
    PROBLEM_DEFINITION,
    RESULT_DEFINITION,
    SOLUTION_DEFINITION,
    ENVIRONMENT_DEFINITION,
    WRITER_DISCOVERY_PROMPT,
    WRITER_REFLECTION_PROMPT,
)
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Abstract language model client for text generation."""

    async def ainvoke(self, prompt: str) -> str:
        """Generate a response from a prompt."""


class EmbedderClient(Protocol):
    """Abstract embedder client for vector embeddings."""

    async def embed(self, text: str) -> list[float]:
        """Create a vector representation of text."""


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

def _extract_json_object(raw: str) -> dict[str, Any]:
    """Extract first JSON object from model output."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Model output is empty.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output does not contain valid JSON object")
        return json.loads(raw[start : end + 1])


def _extract_json_payload(raw: str) -> Any:
    """Extract a JSON object or array from model output."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Model output is empty.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for open_char, close_char in (("[", "]"), ("{", "}")):
            start = raw.find(open_char)
            end = raw.rfind(close_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError("Model output does not contain valid JSON payload")


class WriterState(TypedDict, total=False):
    """LangGraph state for writer pipeline."""

    text: str
    environment_hint: str
    extractions: list[dict[str, str]]  # Multiple extractions per text
    reflections: list[dict[str, Any]]  # Multiple reflections
    embeddings_list: list[dict[str, list[float]]]  # Multiple embedding sets
    persisted: list[dict[str, Any]]  # Multiple persisted entries
    errors: list[str]


def build_submitter_graph(
    db: DatabaseManager,
    llm: LLMClient | None = None,
    embedder: EmbedderClient | None = None,
):
    """Build and compile writer graph."""
    embedder_client = embedder

    async def discovery_node(state: WriterState) -> WriterState:
        text = state.get("text", "").strip()
        environment = state.get("environment_hint", "").strip() or "auto"
        errors = list(state.get("errors", []))
        if not text:
            errors.append("Writer input text is empty.")
            return {"errors": errors}

        prompt = WRITER_DISCOVERY_PROMPT.format(
            problem_definition=PROBLEM_DEFINITION.strip(),
            solution_definition=SOLUTION_DEFINITION.strip(),
            result_definition=RESULT_DEFINITION.strip(),
            environment_definition=ENVIRONMENT_DEFINITION.split(),
            environment=environment,
            text=text,
        )
        raw = await llm.ainvoke(prompt)
        extractions = []

        try:
            raw_data = _extract_json_payload(raw)
        except ValueError as exc:
            errors.append(str(exc))
            errors.append("Discovery node failed to parse model output.")
            return {"errors": errors}

        if raw_data is None:
            errors.append("Discovery node produced null JSON payload.")
            return {"errors": errors}

        if isinstance(raw_data, dict):
            raw_data = [raw_data]
        if not isinstance(raw_data, list):
            errors.append("Discovery node returned JSON payload of wrong type.")
            return {"errors": errors}

        for item in raw_data:
            try:
                extraction = WriterExtraction.model_validate(item)
                extractions.append(extraction.model_dump())
            except Exception as exc:
                errors.append(f"Discovery output item validation failed: {exc}")

        if not extractions:
            errors.append("No extractions produced from discovery node.")
            return {"errors": errors}

        return {"extractions": extractions, "errors": errors}

    async def reflection_node(state: WriterState) -> WriterState:
        extractions_raw = state.get("extractions", [])
        errors = list(state.get("errors", []))
        if not extractions_raw:
            errors.append("Cannot reflect without extraction payloads.")
            return {"errors": errors}

        reflections = []
        for extraction_raw in extractions_raw:
            extraction = WriterExtraction.model_validate(extraction_raw)

            prompt = WRITER_REFLECTION_PROMPT.format(
                problem=extraction.problem,
                solution=extraction.solution,
                mechanism=extraction.mechanism,
                result=extraction.result,
                environment=extraction.environment,
            )
            raw = await llm.ainvoke(prompt)

            reflection = WriterReflection.model_validate(_extract_json_object(raw))
            reflections.append(reflection.model_dump())
        
        return {"reflections": reflections, "errors": errors}

    async def embed_node(state: WriterState) -> WriterState:
        extractions_raw = state.get("extractions", [])
        errors = list(state.get("errors", []))
        if not extractions_raw:
            errors.append("Cannot embed without extraction payloads.")
            return {"errors": errors}

        embeddings_list = []
        for extraction_raw in extractions_raw:
            extraction = WriterExtraction.model_validate(extraction_raw)
            embeddings = {
                "environment": await embedder_client.embed(extraction.environment),
                "problem": await embedder_client.embed(extraction.problem),
                "solution": await embedder_client.embed(extraction.solution),
                "mechanism": await embedder_client.embed(extraction.mechanism),
                "result": await embedder_client.embed(extraction.result),
            }
            embeddings_list.append(embeddings)
        
        return {"embeddings_list": embeddings_list, "errors": errors}

    async def persist_node(state: WriterState) -> WriterState:
        extractions_raw = state.get("extractions", [])
        reflections_raw = state.get("reflections", [])
        embeddings_list = state.get("embeddings_list", [])
        errors = list(state.get("errors", []))
        
        if not extractions_raw or not reflections_raw or not embeddings_list:
            errors.append("Persistence requires extractions, reflections, and embeddings.")
            return {"errors": errors}

        if len(extractions_raw) != len(reflections_raw) or len(extractions_raw) != len(embeddings_list):
            errors.append("Extraction, reflection, and embeddings count mismatch.")
            return {"errors": errors}

        persisted_entries = []
        for extraction_raw, reflection_raw, embeddings in zip(
            extractions_raw, reflections_raw, embeddings_list
        ):
            extraction = WriterExtraction.model_validate(extraction_raw)
            reflection = WriterReflection.model_validate(reflection_raw)
            row = await db.persist_knowledge(
                extraction=extraction.model_dump(),
                reflection=reflection.model_dump(),
                embeddings=embeddings,
            )
            persisted_entries.append(row)
        
        return {"persisted": persisted_entries, "errors": errors}

    graph = StateGraph(WriterState)
    graph.add_node("discover", discovery_node)
    graph.add_node("reflect", reflection_node)
    graph.add_node("embed", embed_node)
    graph.add_node("persist", persist_node)
    graph.add_edge(START, "discover")
    graph.add_edge("discover", "reflect")
    graph.add_edge("reflect", "embed")
    graph.add_edge("embed", "persist")
    graph.add_edge("persist", END)
    return graph.compile()
