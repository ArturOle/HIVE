import operator

from typing import Any, Annotated
from pydantic import BaseModel, Field, ConfigDict, SkipValidation

from database.manager import DatabaseManager
from ai.providers.abstract_provider import AbstractProviderLLMClient, AbstractProviderEmbedderClient


class AdvancedReaderAgentState(BaseModel):
    """State for the Advanced Reader Agent."""

    query: str
    top_k: int | None

    query_embedding: list[float | int] = Field(default_factory=list)

    search_target: dict[str, str | float] | None = None
    concepts_from_query: dict[str, Any] = Field(default_factory=dict)
    eval_resoning: str = ""

    concepts_from_knowledge_base: dict[str, Any] = Field(default_factory=dict)

    errors: list[str] = Field(default_factory=list)
    llm_response: str | None = None


class AdvancedAgentContext(BaseModel):
    """Context for the Advanced Reader Agent. """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: SkipValidation["DatabaseManager"]
    llm: SkipValidation["AbstractProviderLLMClient"]
    embedder: SkipValidation["AbstractProviderEmbedderClient"]
