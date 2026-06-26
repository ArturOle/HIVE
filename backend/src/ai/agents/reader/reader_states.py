import operator

from typing import Annotated
from pydantic import BaseModel, Field

from src.ai.models import Concept
from src.database.manager import DatabaseManager
from backend.src.ai.providers.abstract_provider import AbstractProviderLLMClient, AbstractProviderEmbedderClient


class AdvancedReaderAgentState(BaseModel):
    """State for the Advanced Reader Agent. """
    
    query: str
    top_k: int | None

    search_target: str | None
    concepts_from_query: Annotated[dict[str, Concept], operator.or_] = Field(default_factory=dict)

    concepts_from_knowledge_base: Annotated[dict[str, Concept], operator.or_] = Field(default_factory=dict)

    errors: list[str]
    llm_response: str | None


class AdvancedReaderAgentContext(BaseModel):
    """Context for the Advanced Reader Agent. """

    db: "DatabaseManager"
    llm: "AbstractProviderLLMClient"
    embedder: "AbstractProviderEmbedderClient"
