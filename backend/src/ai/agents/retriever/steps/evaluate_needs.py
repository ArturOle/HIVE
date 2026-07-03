
import logging
from typing import Any

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


logger = logging.getLogger(__name__)


def _get_state_value(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


class EvalFields(BaseModel):
    reasoning: str
    primary_intent: dict[str, str | float]
    additional_concepts: dict[str, list[dict[str, str | int | float]]]


async def evaluate_needs(
    state: AdvancedReaderAgentState,
    context: AdvancedAgentContext
) -> dict[str, any]:
    """ Evaluate the needs of the user based on the query and knowledge base.
    This function analyses the user's query for the target concept and the provided hints/context for relevant concepts.
    
    Arguments:
        state: Holds changing state of the graph
        context: Holds references to system objects
    
    """
    user_query = str(_get_state_value(state, "query", "")).strip()
    errors = list(_get_state_value(state, "errors", []))
    embedder = getattr(context, "embedder", None)

    if not embedder:
        errors.append("Embedder is unavailable")
        return {"errors": errors}

    user_query_embedding = await embedder.embed(user_query)

    if not user_query:
        errors.append("Reader query text is empty.")
        return {"errors": errors}

    primary_intent = {}
    additional_concepts = {}
    reasoning = ''

    evaluate_prompt = EVALUATE_NEEDS_PROMPT.format(
        environment=ENVIRONMENT_DEFINITION,
        problem=PROBLEM_DEFINITION,
        solution=SOLUTION_DEFINITION,
        mechanism=MECHANISM_DEFINITION,
        result=RESULT_DEFINITION,
        query=user_query
    )
    llm = getattr(context, "llm", None)
    if not llm:
        errors.append("LLM is unavailable")
        return {"errors": errors}

    raw = await llm.ainvoke(evaluate_prompt)

    try:
        eval_results = EvalFields.model_validate_json(raw)
        primary_intent = eval_results.primary_intent
        additional_concepts = eval_results.additional_concepts
        reasoning = eval_results.reasoning
    except (ValueError, ValidationError) as exc:
        logger.warning("fReader parse failed, fallback enabled: %s", exc)
        errors.append(str(exc))

    return {
        "query_embedding": user_query_embedding,
        "search_target": primary_intent,
        "concepts_from_query": additional_concepts,
        "eval_resoning": reasoning,
        "errors": errors,
    }
'{\n  "reasoning": "The query asks for illnesses that cause fever, which is a problem (fever) the user wants to understand, so the primary intent is the problem field.",\n  "primary_intent": {\n    "field": "problem",\n    "weight": 9.0\n  },\n  "additional_concepts": {\n    "environment": [\n      {\n        "value": "illnesses",\n        "weight": 5\n      }\n    ],\n    "problem": [],\n    "solution": [],\n    "mechanism": [],\n    "result": []\n  }\n}'