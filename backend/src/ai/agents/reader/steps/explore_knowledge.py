import os
import logging

from multiprocessing import Pool, TimeoutError

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
from backend.src.database.manager import DatabaseManager


logger = logging.getLogger(__name__)

class ExplorationResultsFields(BaseModel):
    reasoning: str
    primary_intent: dict[str, str]
    additional_concepts: dict[str, list[dict[str, str | int]]]


async def explore_knowledge(
    state: AdvancedReaderAgentState,
    context: AdvancedReaderAgentContext
):
    """ Evaluate the needs of the user based on the query and knowledge base.
    This function analyses the user's query for the target concept and the provided hints/context for relevant concepts.
    
    Arguments:
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
        with Pool(processes=4) as pool:
            # 2. run the simillarity search based on the additional concepts provided in query (from most important)
            suppl_ctx_srch_res = {
                concept: pool.apply_async(
                    func=context.db.search_concept_nodes,
                    kwargs={
                        "label": concept.capitalize(),
                        "embedding": query_embedding,
                        "top_k": top_k,
                    }
                ) for concept in concepts_from_query
            }
    # 3. Merge results

    # 4 for the results of step 2, explore for target

    # 5. join results and save


