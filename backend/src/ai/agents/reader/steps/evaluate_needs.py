
import logging

from pydantic import BaseModel, ValidationError

from backend.src.ai.agents.reader.reader_states import AdvancedReaderAgentContext, AdvancedReaderAgentState
from backend.src.ai.prompts import (
    EVALUATE_NEEDS_PROMPT,
    ENVIRONMENT_DEFINITION,
    PROBLEM_DEFINITION,
    SOLUTION_DEFINITION,
    MECHANISM_DEFINITION,
    RESULT_DEFINITION,
)


logger = logging.getLogger(__name__)

class EvalFields(BaseModel):
    reasoning: str
    primary_intent: dict[str, str]
    additional_concepts: dict[str, list[dict[str, str | int]]]


async def evaluate_needs(
    state: AdvancedReaderAgentState,
    context: AdvancedReaderAgentContext
):
    """ Evaluate the needs of the user based on the query and knowledge base.
    This function analyses the user's query for the target concept and the provided hints/context for relevant concepts.
    
    Arguments:
        state: Holds changing state of the graph
        context: Holds references to system objects
    
    """
    user_query = state.get("query", "").strip()
    errors = errors = list(state.get("errors", []))

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
    raw = await context.llm.ainvoke(evaluate_prompt)

    try:
        eval_results = EvalFields.model_validate_json(raw)
        primary_intent = eval_results.primary_intent
        additional_concepts = eval_results.additional_concepts
        reasoning = eval_results.reasoning
    except (ValueError, ValidationError) as exc:
        logger.warning("fReader parse failed, fallback enabled: {exc}")
        errors.append(exc)
    
    return {
        "search_target": primary_intent,
        "concepts_from_query": additional_concepts,
        "eval_resoning": reasoning,
        "errors": errors
    }
