"""Writer agent LangGraph workflow for storing knowledge in Neo4j."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError, field_validator

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


class WriterState(TypedDict, total=False):
    """LangGraph state for writer pipeline."""

    text: str
    environment_hint: str
    extractions: list[dict[str, str]]  # Multiple extractions per text
    reflections: list[dict[str, Any]]  # Multiple reflections
    embeddings_list: list[dict[str, list[float]]]  # Multiple embedding sets
    persisted: list[dict[str, Any]]  # Multiple persisted entries
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
            return {"extractions": [extraction.model_dump()], "errors": errors}

        prompt = WRITER_DISCOVERY_PROMPT.format(
            problem_definition=PROBLEM_DEFINITION.strip(),
            solution_definition=SOLUTION_DEFINITION.strip(),
            result_definition=RESULT_DEFINITION.strip(),
            environment=environment,
            text=text,
        )
        raw = await llm.ainvoke(prompt)
        extractions = []
        
        # Add validation for empty response
        if not raw or not raw.strip():
            logger.warning("LLM returned empty response. Using fallback extraction.")
            extraction = _heuristic_extract(text, environment)
            extractions = [extraction.model_dump()]
            return {"extractions": extractions, "errors": errors}
        
        try:
            # Parse as JSON array
            raw_data = json.loads(raw)
            if not isinstance(raw_data, list):
                # If it's a single object, wrap it in a list
                raw_data = [raw_data]
            
            for item in raw_data:
                extraction = WriterExtraction.model_validate(item)
                extractions.append(extraction.model_dump())
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning("Discovery parse failed, fallback enabled: %s\nRaw response: %s", exc, raw[:500])
            extraction = _heuristic_extract(text, environment)
            extractions = [extraction.model_dump()]
        
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
            
            if llm is None:
                reflection = WriterReflection(
                    grade=3.0,
                    reasoning="Fallback reflection: moderate confidence due to missing LLM.",
                    key_lesson="Measure outcomes and iterate in the same environment.",
                    risk_factors="Changes in constraints may invalidate this solution.",
                )
                reflections.append(reflection.model_dump())
                continue

            prompt = WRITER_REFLECTION_PROMPT.format(
                problem=extraction.problem,
                solution=extraction.solution,
                mechanism=extraction.mechanism,
                result=extraction.result,
                environment=extraction.environment,
            )
            raw = await llm.ainvoke(prompt)
            
            # Check for empty response
            if not raw or not raw.strip():
                logger.warning("LLM returned empty response for reflection. Using fallback.")
                reflection = WriterReflection(
                    grade=2.5,
                    reasoning="LLM returned empty response.",
                    key_lesson="Check LLM provider configuration and API keys.",
                    risk_factors="LLM service may be unavailable or improperly configured.",
                )
                reflections.append(reflection.model_dump())
                continue
            
            try:
                reflection = WriterReflection.model_validate(_extract_json_object(raw))
            except (ValueError, ValidationError) as exc:
                logger.warning("Reflection parse failed for extraction, using fallback grade: %s\nRaw response: %s", exc, raw[:500])
                reflection = WriterReflection(
                    grade=2.5,
                    reasoning="Model output parse failure; defaulted to conservative grade.",
                    key_lesson="Capture clean metrics before grading outcome quality.",
                    risk_factors="Unknown due to incomplete reflection output.",
                )
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
