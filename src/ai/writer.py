"""Writer agent LangGraph workflow for storing knowledge in Neo4j."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.ai.prompts import (
    PROBLEM_DEFINITION,
    RESULT_DEFINITION,
    SOLUTION_DEFINITION,
    WRITER_DISCOVERY_PROMPT,
    WRITER_REFLECTION_PROMPT,
)
from src.database.manager import DatabaseManager

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


class WriterReflection(BaseModel):
    """Validated reflection contract for quality metadata."""

    grade: float = Field(ge=0.0, le=5.0)
    reasoning: str
    key_lesson: str
    risk_factors: str


class WriterState(TypedDict, total=False):
    """LangGraph state for writer pipeline."""

    text: str
    environment_hint: str
    extraction: dict[str, str]
    reflection: dict[str, Any]
    embeddings: dict[str, list[float]]
    persisted: dict[str, Any]
    errors: list[str]


@dataclass(slots=True)
class DeterministicEmbedder:
    """Fallback deterministic embedder for local/dev execution."""

    dimensions: int = 32

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [digest[i % len(digest)] / 255.0 for i in range(self.dimensions)]
        return values


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Extract first JSON object from model output."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output does not contain valid JSON object")
        return json.loads(raw[start : end + 1])


def _heuristic_extract(text: str, environment_hint: str) -> WriterExtraction:
    """Safe fallback extraction when no model is configured."""
    sentence = text.strip().split(".")[0].strip() or text.strip()
    inferred_environment = environment_hint.strip()
    if inferred_environment.lower() in {"", "general", "unknown", "auto"}:
        inferred_environment = (
            "Inferred from text context: domain-specific operating constraints and "
            "entities directly tied to the extracted problem-solution pair."
        )
    return WriterExtraction(
        environment=inferred_environment,
        problem=sentence or "unknown problem",
        solution=sentence or "unknown solution",
        mechanism="Solution should reduce the key constraint in this environment.",
        result="Result not explicitly provided; inferred from the source text.",
    )


def build_writer_graph(
    db: DatabaseManager,
    llm: LLMClient | None = None,
    embedder: EmbedderClient | None = None,
):
    """Build and compile writer graph."""
    embedder_client = embedder or DeterministicEmbedder()

    async def discovery_node(state: WriterState) -> WriterState:
        text = state.get("text", "").strip()
        environment = state.get("environment_hint", "").strip() or "auto"
        errors = list(state.get("errors", []))
        if not text:
            errors.append("Writer input text is empty.")
            return {"errors": errors}

        if llm is None:
            extraction = _heuristic_extract(text, environment)
            return {"extraction": extraction.model_dump(), "errors": errors}

        prompt = WRITER_DISCOVERY_PROMPT.format(
            problem_definition=PROBLEM_DEFINITION.strip(),
            solution_definition=SOLUTION_DEFINITION.strip(),
            result_definition=RESULT_DEFINITION.strip(),
            environment=environment,
            text=text,
        )
        raw = await llm.ainvoke(prompt)
        try:
            extraction = WriterExtraction.model_validate(_extract_json_object(raw))
        except (ValueError, ValidationError) as exc:
            logger.warning("Discovery parse failed, fallback enabled: %s", exc)
            extraction = _heuristic_extract(text, environment)
        return {"extraction": extraction.model_dump(), "errors": errors}

    async def reflection_node(state: WriterState) -> WriterState:
        extraction_raw = state.get("extraction")
        errors = list(state.get("errors", []))
        if not extraction_raw:
            errors.append("Cannot reflect without extraction payload.")
            return {"errors": errors}

        extraction = WriterExtraction.model_validate(extraction_raw)
        if llm is None:
            reflection = WriterReflection(
                grade=3.0,
                reasoning="Fallback reflection: moderate confidence due to missing LLM.",
                key_lesson="Measure outcomes and iterate in the same environment.",
                risk_factors="Changes in constraints may invalidate this solution.",
            )
            return {"reflection": reflection.model_dump(), "errors": errors}

        prompt = WRITER_REFLECTION_PROMPT.format(
            problem=extraction.problem,
            solution=extraction.solution,
            mechanism=extraction.mechanism,
            result=extraction.result,
            environment=extraction.environment,
        )
        raw = await llm.ainvoke(prompt)
        try:
            reflection = WriterReflection.model_validate(_extract_json_object(raw))
        except (ValueError, ValidationError) as exc:
            logger.warning("Reflection parse failed, using fallback grade: %s", exc)
            reflection = WriterReflection(
                grade=2.5,
                reasoning="Model output parse failure; defaulted to conservative grade.",
                key_lesson="Capture clean metrics before grading outcome quality.",
                risk_factors="Unknown due to incomplete reflection output.",
            )
        return {"reflection": reflection.model_dump(), "errors": errors}

    async def embed_node(state: WriterState) -> WriterState:
        extraction_raw = state.get("extraction")
        errors = list(state.get("errors", []))
        if not extraction_raw:
            errors.append("Cannot embed without extraction payload.")
            return {"errors": errors}

        extraction = WriterExtraction.model_validate(extraction_raw)
        embeddings = {
            "environment": await embedder_client.embed(extraction.environment),
            "problem": await embedder_client.embed(extraction.problem),
            "solution": await embedder_client.embed(extraction.solution),
            "mechanism": await embedder_client.embed(extraction.mechanism),
            "result": await embedder_client.embed(extraction.result),
        }
        return {"embeddings": embeddings, "errors": errors}

    async def persist_node(state: WriterState) -> WriterState:
        extraction_raw = state.get("extraction")
        reflection_raw = state.get("reflection")
        embeddings = state.get("embeddings")
        errors = list(state.get("errors", []))
        if not extraction_raw or not reflection_raw or not embeddings:
            errors.append("Persistence requires extraction, reflection, and embeddings.")
            return {"errors": errors}

        extraction = WriterExtraction.model_validate(extraction_raw)
        reflection = WriterReflection.model_validate(reflection_raw)
        row = await db.persist_knowledge(
            extraction=extraction.model_dump(),
            reflection=reflection.model_dump(),
            embeddings=embeddings,
        )
        return {"persisted": row, "errors": errors}

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
