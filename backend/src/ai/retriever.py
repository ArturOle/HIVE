"""Reader agent LangGraph workflow for concept-aware retrieval."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from math import sqrt
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError

from src.ai.prompts import COMPOSE_RESPONSE_PROMPT, READER_CONCEPT_PARSE_PROMPT
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


class ReaderConcepts(BaseModel):
    """Concept parsing contract for retrieval queries."""

    environment: str | None = None
    problem: str | None = None
    solution: str | None = None
    mechanism: str | None = None
    result: str | None = None


class ReaderState(TypedDict, total=False):
    """LangGraph state for reader pipeline."""

    query: str
    top_k: int | None
    concepts: dict[str, str | None]
    concept_embeddings: dict[str, list[float]]
    concept_hits: dict[str, list[dict[str, Any]]]
    ranked: list[dict[str, Any]]
    alternatives: list[dict[str, Any]]
    response: dict[str, Any]
    errors: list[str]
    llm_response: str | None


@dataclass(slots=True)
class DeterministicEmbedder:
    """Fallback deterministic embedder for local/dev execution."""

    dimensions: int = 32

    async def embed(self, text: str) -> list[float]:
        import hashlib

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self.dimensions)]


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


def _heuristic_parse(query: str) -> ReaderConcepts:
    """Fallback concept parsing using a minimal heuristic."""
    text = query.strip()
    return ReaderConcepts(problem=text or None)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_retriever_graph(
    db: DatabaseManager,
    llm: LLMClient,
    embedder: EmbedderClient,
):
    target_similarity = 0.90
    adaptive_step = 10
    adaptive_cap = 120

    """Build and compile reader graph."""
    embedder_client = embedder
    concept_labels = {
        "environment": "Environment",
        "problem": "Problem",
        "solution": "Solution",
        "mechanism": "Mechanism",
        "result": "Result",
    }

    async def parse_query_node(state: ReaderState) -> ReaderState:
        query = state.get("query", "").strip()
        errors = list(state.get("errors", []))
        if not query:
            errors.append("Reader query text is empty.")
            return {"errors": errors}

        if llm is None:
            concepts = _heuristic_parse(query)
            return {"concepts": concepts.model_dump(), "errors": errors}

        prompt = READER_CONCEPT_PARSE_PROMPT.format(query=query)
        raw = await llm.ainvoke(prompt)
        try:
            concepts = ReaderConcepts.model_validate(_extract_json_object(raw))
        except (ValueError, ValidationError) as exc:
            logger.warning("Reader parse failed, fallback enabled: %s", exc)
            concepts = _heuristic_parse(query)
        return {"concepts": concepts.model_dump(), "errors": errors}

    async def concept_search_node(state: ReaderState) -> ReaderState:
        concepts_raw = state.get("concepts", {})
        errors = list(state.get("errors", []))
        requested_top_k = state.get("top_k")
        concept_embeddings: dict[str, list[float]] = {}
        concept_hits: dict[str, list[dict[str, Any]]] = {}

        for concept, label in concept_labels.items():
            value = concepts_raw.get(concept)
            if not value:
                continue

            query_embedding = await embedder_client.embed(value)
            concept_embeddings[concept] = query_embedding

            effective_limit = int(requested_top_k) if requested_top_k else adaptive_step
            rows: list[dict[str, Any]] = []
            while True:
                try:
                    rows = await db.search_concept_nodes(
                        label=label,
                        embedding=query_embedding,
                        top_k=effective_limit,
                    )
                except Exception as exc:  # pragma: no cover - depends on Neo4j capabilities
                    logger.warning(
                        "Vector similarity query failed for %s, using fallback ranking: %s",
                        concept,
                        exc,
                    )
                    fallback = await db.search_concept_nodes(
                        label=label,
                        embedding=query_embedding,
                        top_k=300,
                    )
                    rows = []
                    for row in fallback:
                        similarity = _cosine_similarity(query_embedding, row.get("embedding", []))
                        rows.append({**row, "similarity": similarity})
                    rows.sort(key=lambda r: float(r.get("similarity", 0.0)), reverse=True)
                    rows = rows[:effective_limit]

                if requested_top_k:
                    break

                best_similarity = float(rows[0].get("similarity", 0.0)) if rows else 0.0
                if best_similarity >= target_similarity or effective_limit >= adaptive_cap:
                    break
                effective_limit = min(effective_limit + adaptive_step, adaptive_cap)

            concept_hits[concept] = rows

        return {
            "concept_embeddings": concept_embeddings,
            "concept_hits": concept_hits,
            "errors": errors,
        }

    async def rank_merge_node(state: ReaderState) -> ReaderState:
        concept_hits = state.get("concept_hits", {})
        errors = list(state.get("errors", []))
        candidate_scores: dict[str, dict[str, Any]] = {}

        for concept, hits in concept_hits.items():
            for hit in hits:
                node_id = hit["node_id"]
                similarity = float(hit.get("similarity", 0.0))
                if node_id not in candidate_scores:
                    candidate_scores[node_id] = {
                        "node_id": node_id,
                        "text": hit.get("text", ""),
                        "concepts_matched": set(),
                        "similarities": [],
                    }
                candidate_scores[node_id]["concepts_matched"].add(concept)
                candidate_scores[node_id]["similarities"].append(similarity)

        ranked = []
        for item in candidate_scores.values():
            sims = item["similarities"]
            avg_similarity = sum(sims) / len(sims) if sims else 0.0
            coverage = len(item["concepts_matched"])
            score = avg_similarity * 0.7 + min(coverage / 5.0, 1.0) * 0.3
            ranked.append(
                {
                    "node_id": item["node_id"],
                    "text": item["text"],
                    "avg_similarity": avg_similarity,
                    "concept_coverage": coverage,
                    "score": score,
                    "concepts_matched": sorted(item["concepts_matched"]),
                }
            )
        ranked.sort(key=lambda r: r["score"], reverse=True)
        requested_top_k = state.get("top_k")
        if requested_top_k:
            trimmed = ranked[: int(requested_top_k)]
        else:
            trimmed = [item for item in ranked if item["avg_similarity"] >= target_similarity]
            if not trimmed:
                trimmed = ranked[:adaptive_step]
        return {"ranked": trimmed, "errors": errors}

    async def traverse_alternatives_node(state: ReaderState) -> ReaderState:
        ranked = state.get("ranked", [])
        errors = list(state.get("errors", []))
        alternatives: list[dict[str, Any]] = []
        for item in ranked:
            result = await db.get_alternative_nodes(node_id=item["node_id"], limit=12)
            if result:
                alternatives.append(
                    {
                        "source_node_id": item["node_id"],
                        "alternatives": result,
                    }
                )
        return {"alternatives": alternatives, "errors": errors}

    async def build_response_node(state: ReaderState) -> ReaderState:
        llm_response = await llm.ainvoke(COMPOSE_RESPONSE_PROMPT.format(
            query=state.get("query", ""),
            ranked=json.dumps(state.get("ranked", []), indent=2),
            alternatives=json.dumps(state.get("alternatives", []), indent=2),
        ))
        return {
            "response": llm_response
        }

    graph = StateGraph(ReaderState)
    graph.add_node("parse_query", parse_query_node)
    graph.add_node("concept_search", concept_search_node)
    graph.add_node("rank_merge", rank_merge_node)
    graph.add_node("traverse_alternatives", traverse_alternatives_node)
    graph.add_node("build_response", build_response_node)
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", "concept_search")
    graph.add_edge("concept_search", "rank_merge")
    graph.add_edge("rank_merge", "traverse_alternatives")
    graph.add_edge("traverse_alternatives", "build_response")
    graph.add_edge("build_response", END)
    return graph.compile()
