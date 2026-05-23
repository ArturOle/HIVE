"""Orchestrator for routing read/write LangGraph workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.ai.reader import build_reader_graph
from src.ai.writer import build_writer_graph
from src.database.manager import DatabaseManager


@dataclass(slots=True)
class OrchestratorConfig:
    """Execution config for read/write routing."""
    default_top_k: int | None = None


class AgentOrchestrator:
    """Coordinates shared resources and two specialized LangGraph workflows."""

    def __init__(
        self,
        db: DatabaseManager | None = None,
        llm: Any | None = None,
        embedder: Any | None = None,
        config: OrchestratorConfig | None = None,
    ) -> None:
        self.db = db or DatabaseManager()
        self.llm = llm
        self.embedder = embedder
        self.config = config or OrchestratorConfig()
        self.writer_graph = None
        self.reader_graph = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database and compile both graphs."""
        if self._initialized:
            return
        await self.db.initialize()
        await self.db.setup_database()
        self.writer_graph = build_writer_graph(
            db=self.db,
            llm=self.llm,
            embedder=self.embedder,
        )
        self.reader_graph = build_reader_graph(
            db=self.db,
            llm=self.llm,
            embedder=self.embedder,
        )
        self._initialized = True

    async def run_write(self, text: str, environment_hint: str = "general") -> dict[str, Any]:
        """Execute writer workflow."""
        if not self.writer_graph:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        result = await self.writer_graph.ainvoke(
            {
                "text": text,
                "environment_hint": environment_hint,
                "errors": [],
            }
        )
        return dict(result)

    async def run_read(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """Execute reader workflow."""
        if not self.reader_graph:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        result = await self.reader_graph.ainvoke(
            {
                "query": query,
                "top_k": top_k if top_k is not None else self.config.default_top_k,
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
        """Route execution to dedicated read or write graph."""
        normalized_mode = mode.strip().lower()
        if normalized_mode == "write":
            return await self.run_write(text=text, environment_hint=environment_hint)
        if normalized_mode == "read":
            return await self.run_read(query=text, top_k=top_k)
        raise ValueError("mode must be either 'read' or 'write'")

    async def close(self) -> None:
        """Release orchestrator resources."""
        await self.db.close()
        self._initialized = False

    async def __aenter__(self) -> "AgentOrchestrator":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
