import logging
from typing import Any

from ai.agents.retriever.models import AdvancedAgentContext, AdvancedReaderAgentState
from database.manager import DatabaseManager


logger = logging.getLogger(__name__)

CONCEPT_LABELS = {
    "environment": "Environment",
    "problem": "Problem",
    "solution": "Solution",
    "mechanism": "Mechanism",
    "result": "Result",
}


def _get_state_value(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _normalize_concept_label(value: str | None) -> str | None:
    if not value:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    return CONCEPT_LABELS.get(normalized.lower(), normalized.title())


def _extract_concept_requests(raw_concepts: Any) -> list[tuple[str, str]]:
    requests: list[tuple[str, str]] = []

    if isinstance(raw_concepts, dict):
        for field, items in raw_concepts.items():
            if not items:
                continue

            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        value = item.get("value")
                        if value is None or str(value).strip() == "":
                            continue
                        requests.append((str(field), str(value)))
                    elif item:
                        requests.append((str(field), str(item)))
            elif items:
                requests.append((str(field), str(items)))
    elif isinstance(raw_concepts, str):
        for concept in [item.strip() for item in raw_concepts.split(",") if item.strip()]:
            requests.append(("problem", concept))

    return requests


async def explore_knowledge(
    state: AdvancedReaderAgentState,
    context: AdvancedAgentContext,
) -> dict[str, Any]:
    """Explore the knowledge base for concepts surfaced by the query analysis.

    The step turns the evaluated query concepts into concrete database searches so
    the later retriever stages can reason over grounded knowledge.
    """
    db_manager: DatabaseManager | None = getattr(context, "db", None)
    query_embedding = _get_state_value(state, "query_embedding", [])
    top_k = _get_state_value(state, "top_k", 10)
    errors = list(_get_state_value(state, "errors", []))

    if not db_manager:
        errors.append("Database is unavailable")
        return {"errors": errors}

    if not query_embedding:
        errors.append("Query embedding is unavailable")
        return {"errors": errors}

    concepts_from_query = _get_state_value(state, "concepts_from_query", {})
    concept_requests = _extract_concept_requests(concepts_from_query)

    concept_hits: dict[str, list[dict[str, Any]]] = {}

    requested_top_k = int(top_k) if top_k is not None else 10

    for field, value in concept_requests:
        label = _normalize_concept_label(field)
        if not label or not value:
            continue

        try:
            rows = await db_manager.search_concept_nodes(
                label=label,
                embedding=query_embedding,
                top_k=requested_top_k,
            )
        except Exception as exc:  # pragma: no cover - depends on DB capabilities
            logger.warning("Knowledge exploration failed for %s: %s", field, exc)
            errors.append(f"Knowledge exploration failed for {field}: {exc}")
            continue

        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            normalized_rows.append(
                {
                    "node_id": row.get("node_id"),
                    "text": row.get("text", ""),
                    "similarity": row.get("similarity", 0.0),
                    "source_concept": value,
                }
            )

        concept_hits[field] = normalized_rows

    return {
        "concepts_from_knowledge_base": concept_hits,
        "errors": errors,
    }
