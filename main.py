"""CLI entrypoint for read/write orchestrator workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from src.ai.providers import (
    GeminiEmbedderClient,
    GeminiLLMClient,
    GeminiProviderConfig,
    OpenAIEmbedderClient,
    OpenAILLMClient,
    OpenAIProviderConfig,
)
from src.logic.orchestrator import AgentOrchestrator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ReLive read/write agent runner")
    parser.add_argument(
        "--mode",
        choices=["read", "write"],
        required=True,
        help="Execution mode",
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Input text (write mode) or query (read mode)",
    )
    parser.add_argument(
        "--environment",
        default="general",
        help="Environment hint for write mode",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Top-k retrieval size for read mode; omit for adaptive traversal",
    )
    parser.add_argument(
        "--provider",
        choices=["none", "openai", "gemini"],
        default="none",
        help="LLM/embedding provider",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    llm = None
    embedder = None
    if args.provider == "openai":
        config = OpenAIProviderConfig.from_env()
        llm = OpenAILLMClient(config)
        embedder = OpenAIEmbedderClient(config)
    elif args.provider == "gemini":
        config = GeminiProviderConfig.from_env()
        llm = GeminiLLMClient(config)
        embedder = GeminiEmbedderClient(config)

    async with AgentOrchestrator(llm=llm, embedder=embedder) as orchestrator:
        result = await orchestrator.run(
            mode=args.mode,
            text=args.text,
            environment_hint=args.environment,
            top_k=args.top_k,
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_run())