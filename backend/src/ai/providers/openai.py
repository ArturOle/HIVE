"""Provider module with OpenAI clients."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from langfuse import observe

from ai.providers.abstract_provider import (
    AbstractProviderLLMClient,
    AbstractProviderEmbedderClient,
)


class OpenAIProviderConfig(BaseSettings):
    """Configuration for Gemini provider clients using Pydantic."""

    # We use SecretStr to prevent the key from being accidentally printed in logs
    api_key: SecretStr = Field(
        alias="OPENAI_API_KEY", 
        validation_alias="OPENAI_API_KEY"
    )
    
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_LLM_MODEL"
    )
    
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",      # Essential so it doesn't crash on Neo4j variables
        case_sensitive=False
    )


class OpenAILLMClient(AbstractProviderLLMClient):
    """Async LLM adapter compatible with writer/reader protocols."""

    def __init__(self, config: OpenAIProviderConfig):
        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required. Install with: pip install openai"
            ) from exc
        self._client = AsyncOpenAI(api_key=config.api_key)
        self._model = config.llm_model

    @observe(as_type="generation")
    async def ainvoke(self, prompt: str) -> str:
        response = await self._client.responses.create(
            model=self._model,
            input=prompt,
            temperature=0.2,
        )
        return response.output_text


class OpenAIEmbedderClient(AbstractProviderEmbedderClient):
    """Async embedding adapter compatible with writer/reader protocols."""

    def __init__(self, config: OpenAIProviderConfig):
        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required. Install with: pip install openai"
            ) from exc
        self._client = AsyncOpenAI(api_key=config.api_key)
        self._model = config.embedding_model

    @observe(as_type="generation")
    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return list(response.data[0].embedding)