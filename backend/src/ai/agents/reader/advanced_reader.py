

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError


class AdvancedReaderAgentState(BaseModel):
    """State for the Advanced Reader Agent. """
    
    query: str
    top_k: int | None

    search_target: str | None
    extracted_concepts: dict[str, str | None]
    
    concept_embeddings: dict[str, list[float]]

    llm_response: str | None


