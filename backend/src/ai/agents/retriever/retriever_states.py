import operator

from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, SkipValidation

from src.ai.models import Concept
from src.database.manager import DatabaseManager
from src.ai.providers.abstract_provider import AbstractProviderLLMClient, AbstractProviderEmbedderClient


class AdvancedReaderAgentState(BaseModel):
    """State for the Advanced Reader Agent. """
    
    query: str
    top_k: int | None

    query_embedding: list[float | int]

    search_target: str | None
    concepts_from_query: Annotated[dict[str, Concept], operator.or_] = Field(default_factory=dict)
    eval_resoning: str

    concepts_from_knowledge_base: Annotated[dict[str, Concept], operator.or_] = Field(default_factory=dict)

    errors: list[str]
    llm_response: str | None


class AdvancedReaderAgentContext(BaseModel):
    """Context for the Advanced Reader Agent. """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: SkipValidation["DatabaseManager"]
    llm: SkipValidation["AbstractProviderLLMClient"]
    embedder: SkipValidation["AbstractProviderEmbedderClient"]
