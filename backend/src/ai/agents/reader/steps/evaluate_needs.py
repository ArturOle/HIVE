

from backend.src.ai.agents.reader.reader_states import AdvancedReaderAgentContext, AdvancedReaderAgentState
from backend.src.ai.prompts import (
    EVALUATE_NEEDS_PROMPT,
    ENVIRONMENT_DEFINITION,
    PROBLEM_DEFINITION,
    SOLUTION_DEFINITION,
    MECHANISM_DEFINITION,
    RESULT_DEFINITION,
)

async def evaluate_needs(
    state: AdvancedReaderAgentState,
    context: AdvancedReaderAgentContext
):
    """ Evaluate the needs of the user based on the query and knowledge base.
    This function analyses the user's query for the target concept and the provided hints/context for relevant concepts.
    eg. How to prevent drone overheating in the tropical forest?"""

    user_query = state.get("query", "").strip()

    evaluate_prompt = EVALUATE_NEEDS_PROMPT.format(
        environment=ENVIRONMENT_DEFINITION,
        problem=PROBLEM_DEFINITION,
        solution=SOLUTION_DEFINITION,
        mechanism=MECHANISM_DEFINITION,
        result=RESULT_DEFINITION,
        query=user_query
    )
