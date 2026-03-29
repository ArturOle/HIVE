"""Provider module with OpenAI clients."""

from __future__ import annotations

import os
from dataclasses import dataclass
from abstract_provider import (
    AbstractProviderConfig,
    AbstractProviderLLMClient,
    AbstractProviderEmbedderClient,
)


@dataclass(slots=True)
class OpenAIProviderConfig(AbstractProviderConfig):
    """Configuration for OpenAI provider clients."""

    api_key: str
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    @classmethod
    def from_env(cls) -> "OpenAIProviderConfig":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return cls(
            api_key=api_key,
            llm_model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
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

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return list(response.data[0].embedding)