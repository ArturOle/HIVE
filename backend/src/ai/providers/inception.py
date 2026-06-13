"""Provider module with Inception Labs Mercury 2 client."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.ai.providers.abstract_provider import (
    AbstractProviderLLMClient,
    AbstractProviderEmbedderClient,
)


class InceptionProviderConfig(BaseSettings):
    """Configuration for Inception Labs Mercury 2 provider."""

    api_key: SecretStr = Field(
        alias="INCEPTION_API_KEY",
        validation_alias="INCEPTION_API_KEY"
    )
    
    llm_model: str = Field(
        default="mercury-2",
        validation_alias="INCEPTION_LLM_MODEL"
    )
    
    base_url: str = Field(
        default="https://api.inceptionlabs.ai/v1",
        validation_alias="INCEPTION_BASE_URL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )


class InceptionLLMClient(AbstractProviderLLMClient):
    """Async LLM adapter for Inception Labs Mercury 2."""

    def __init__(self, config: InceptionProviderConfig):
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "LangChain OpenAI SDK is required. Install with: pip install langchain-openai"
            ) from exc
        
        self._client = ChatOpenAI(
            model=config.llm_model,
            temperature=0.02,
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url
        )

    async def ainvoke(self, prompt: str) -> str:
        """Invoke Mercury 2 LLM with the given prompt."""
        from langchain_core.messages import HumanMessage
        
        try:
            # Use async invoke if available, otherwise use invoke with asyncio
            response = await self._client.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except AttributeError:
            # Fallback for sync-only mode
            import asyncio
            response = await asyncio.to_thread(
                self._client.invoke,
                [HumanMessage(content=prompt)]
            )
            return response.content


class InceptionEmbedderClient(AbstractProviderEmbedderClient):
    """Async embedding adapter for Inception Labs (if Mercury 2 supports embeddings)."""

    def __init__(self, config: InceptionProviderConfig):
        """Initialize embedder. Note: Mercury 2 may not support embeddings directly."""
        try:
            from langchain_openai import OpenAIEmbeddings
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "LangChain OpenAI SDK is required. Install with: pip install langchain-openai"
            ) from exc
        
        self._client = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url
        )

    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using Inception Labs endpoint."""
        import asyncio
        
        try:
            embedding = await asyncio.to_thread(self._client.embed_query, text)
            return embedding
        except Exception as exc:
            # Mercury 2 may not support embeddings; fall back to error
            raise RuntimeError(
                f"Inception Labs Mercury 2 embeddings not available: {exc}"
            ) from exc
