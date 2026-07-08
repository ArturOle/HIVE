
import logging
import json

from ai.agents.retriever.models import AdvancedAgentContext, AdvancedReaderAgentState
from ai.prompts import COMPOSE_RESPONSE_PROMPT


logger = logging.getLogger(__name__)


async def review_quality(
    state: AdvancedReaderAgentState,
    context: AdvancedAgentContext
) -> dict[str, any]:
    llm_response = await context.llm.ainvoke(COMPOSE_RESPONSE_PROMPT.format(
        query=state.get("query", ""),
        ranked=json.dumps(state.get("ranked", []), indent=2),
        alternatives=json.dumps(state.get("alternatives", []), indent=2),
    ))
    logger.info("The LLM response step executed succesfully.")
    return {
        "response": llm_response
    }
