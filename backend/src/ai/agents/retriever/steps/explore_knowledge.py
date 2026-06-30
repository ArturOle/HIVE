import os
import logging

from multiprocessing import Pool, TimeoutError

from pydantic import BaseModel, ValidationError

from ai.agents.retriever.models import AdvancedAgentContext, AdvancedReaderAgentState
from ai.prompts import (
    EVALUATE_NEEDS_PROMPT,
    ENVIRONMENT_DEFINITION,
    PROBLEM_DEFINITION,
    SOLUTION_DEFINITION,
    MECHANISM_DEFINITION,
    RESULT_DEFINITION,
)
from database.manager import DatabaseManager


logger = logging.getLogger(__name__)

class ExplorationResultsFields(BaseModel):
    reasoning: str
    primary_intent: dict[str, str]
    additional_concepts: dict[str, list[dict[str, str | int]]]


async def explore_knowledge(
    state: AdvancedReaderAgentState,
    context: AdvancedAgentContext
):
    """ Evaluate the needs of the user based on the query and knowledge base.
    This function analyses the user's query for the target concept and the provided hints/context for relevant concepts.
    
    Args:
        state: Holds changing state of the graph
        context: Holds references to system objects
    
    """
    db_manager: DatabaseManager = context.get("db", '')
    query_embedding = state.get("query_embedding", [])
    top_k = state.get("top_k", 10)
    errors = list(context.get("errors", []))
    
    if not db_manager:
        errors.append("Database is unavilable")
        return {"errors": errors}
    
    if not query_embedding:
        errors.append("Query embedding is unavailable")
        return {"errors": errors}


    # 1. get the main target and concepts
    search_target = state.get("search_target", "").strip()
    concepts_from_query = state.get("concepts_from_query", "").strip()
    suppl_ctx_srch_res = {}
    if concepts_from_query:
        # 2. run the simillarity search based on the additional concepts provided in query (from most important)
        # 3. Merge results
        # 4 for the results of step 2, explore for target
        # 5. join results and save
        suppl_ctx_srch_res = context.db.search_concept_nodes_parallel(
            labels=concepts_from_query,
            embedding=query_embedding,
            top_k=top_k
        )

async def concept_search_node(
    state: AdvancedReaderAgentState,
    context: AdvancedAgentContext
) -> AdvancedReaderAgentState:
    target_similarity = 0.90
    adaptive_step = 10
    adaptive_cap = 120
    concept_labels = {
        "environment": "Environment",
        "problem": "Problem",
        "solution": "Solution",
        "mechanism": "Mechanism",
        "result": "Result",
    }
    concepts_raw = state.get("concepts", {})
    errors = list(state.get("errors", []))
    requested_top_k = state.get("top_k")
    concept_embeddings: dict[str, list[float]] = {}
    concept_hits: dict[str, list[dict[str, any]]] = {}

    for concept, label in concept_labels.items():
        value = concepts_raw.get(concept)
        if not value:
            continue

        query_embedding = await context.embedder.embed(value)
        concept_embeddings[concept] = query_embedding

        effective_limit = int(requested_top_k) if requested_top_k else adaptive_step
        rows: list[dict[str, any]] = []
        while True:
            try:
                rows = await context.db.search_concept_nodes(
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
                fallback = await context.db.search_concept_nodes(
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