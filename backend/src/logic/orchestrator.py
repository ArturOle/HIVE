"""Orchestrator for routing read/write LangGraph workflows."""
from __future__ import annotations

from typing import Any

from src.ai.agents.retriever.advanced_retriever import build_advanced_retriever_graph
from backend.src.ai.agents.retriever.models import AdvancedAgentContext
from src.ai.providers.abstract_provider import AbstractProviderLLMClient, AbstractProviderEmbedderClient
from src.ai.retriever import build_retriever_graph
from src.ai.submitter import build_submitter_graph
from src.database.manager import DatabaseManager

from dotenv import load_dotenv


load_dotenv("/home/r2/Documents/Projects/HIVE/backend/.env")


class AgentOrchestrator:
    """Coordinates shared resources and specialized LangGraph workflows."""

    def __init__(
        self,
        db: DatabaseManager,
        llm: AbstractProviderLLMClient,
        embedder: AbstractProviderEmbedderClient,
        top_k: int,
    ) -> None:
        self.context = AdvancedAgentContext(
            db=db,
            llm=llm,
            embedder=embedder,
        )
        self.top_k = top_k
        self.submit_graph = None
        self.retrieve_graph = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database and compile both graphs."""
        if self._initialized:
            return

        await self.context.db.initialize()
        await self.context.db.setup_database()

        self.submit_graph = build_submitter_graph(
            db=self.context.db,
            llm=self.context.llm,
            embedder=self.context.embedder,
        )
        self.retrieve_graph = build_retriever_graph(
            db=self.context.db,
            llm=self.context.llm,
            embedder=self.context.embedder,
        )
        self.advanced_retrieve_graph = build_advanced_retriever_graph(
            context=self.context
        )

        self._initialized = True

    async def run_submit(self, text: str, environment_hint: str = "") -> dict[str, Any]:
        """Execute submit workflow."""
        if not self.submit:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        result = await self.submit_graph.ainvoke(
            {
                "text": text,
                "environment_hint": environment_hint,
                "errors": [],
            }
        )
        return dict(result)

    async def run_retrieve(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """Execute reader workflow."""
        if not self.retrieve_graph:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        result = await self.retrieve_graph.ainvoke(
            {
                "query": query,
                "top_k": top_k if top_k is not None else self.top_k,
                "errors": [],
            }
        )
        return dict(result)

    async def run_advanced_retrieve(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """Execute advanced retriever workflow."""
        if not self.advanced_retrieve_graph:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        result = await self.advanced_retrieve_graph.ainvoke(
            {
                "query": query,
                "top_k": top_k if top_k is not None else self.top_k,
                "errors": [],
            }
        )
        return dict(result)

    async def run(
        self,
        mode: str,
        text: str,
        environment_hint: str = "general",
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Route execution to dedicated retrieve or submit graph."""

        match mode.strip().lower():
            case "submit":
                return await self.run_submit(text=text, environment_hint=environment_hint)
            case "retrieve":
                return await self.run_retrieve(query=text, top_k=top_k)
            case "advanced_retrieve":
                return await self.run_advanced_retrieve(query=text, top_k=top_k)
            case _:
                raise ValueError("Mode must be either 'advanced_retrieve', 'retrieve' or 'submit'.")

    async def close(self) -> None:
        """Release orchestrator resources."""
        await self.context.db.close()
        self._initialized = False

    async def __aenter__(self) -> "AgentOrchestrator":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
