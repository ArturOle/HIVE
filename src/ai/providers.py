"""Provider module with OpenAI and Gemini clients."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


@dataclass(slots=True)
class OpenAIProviderConfig:
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


class OpenAILLMClient:
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


class OpenAIEmbedderClient:
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


@dataclass(slots=True)
class GeminiProviderConfig:
    """Configuration for Gemini provider clients."""

    api_key: str
    llm_model: str = "gemini-2.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"

    @classmethod
    def from_env(cls) -> "GeminiProviderConfig":
        api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv(
            "GOOGLE_API_KEY", ""
        ).strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
        return cls(
            api_key=api_key,
            llm_model=os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash-lite"),
            embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        )


class GeminiLLMClient:
    """Async Gemini LLM adapter compatible with writer/reader protocols."""

    def __init__(self, config: GeminiProviderConfig):
        try:
            import google.generativeai as genai  # type: ignore[reportMissingImports]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Gemini SDK is required. Install with: pip install google-generativeai"
            ) from exc
        genai.configure(api_key=config.api_key)
        self._genai = genai
        self._model = config.llm_model

    async def ainvoke(self, prompt: str) -> str:
        model = self._genai.GenerativeModel(self._model)
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = getattr(response, "text", None)
        return text or ""


class GeminiEmbedderClient:
    """Async Gemini embedding adapter compatible with writer/reader protocols."""

    def __init__(self, config: GeminiProviderConfig):
        try:
            import google.generativeai as genai  # type: ignore[reportMissingImports]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Gemini SDK is required. Install with: pip install google-generativeai"
            ) from exc
        genai.configure(api_key=config.api_key)
        self._genai = genai
        self._model = config.embedding_model

    async def embed(self, text: str) -> list[float]:
        response = await asyncio.to_thread(
            self._genai.embed_content,
            model=self._model,
            content=text,
            task_type="retrieval_document",
        )
        vector = response.get("embedding", [])
        return [float(v) for v in vector]
