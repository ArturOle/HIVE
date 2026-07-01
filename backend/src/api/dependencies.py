"""Orchestrator lifecycle management: startup/shutdown wiring and DI accessor."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from ai.providers.qwen import QwenEmbedderClient, QwenLLMClient, QwenProviderConfig
from database.config import Neo4jSettings, load_project_env
from database.manager import DatabaseManager
from logic.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

# Module-level singleton, populated during the app lifespan.
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """FastAPI dependency: returns the initialized orchestrator or raises 503."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return _orchestrator


async def _build_orchestrator(neo4j_settings: Neo4jSettings) -> AgentOrchestrator:
    """Construct and initialize the orchestrator, with friendly error logging."""
    try:
        llm = QwenLLMClient(QwenProviderConfig())
        embedder = QwenEmbedderClient(QwenProviderConfig())
        db = DatabaseManager(settings=neo4j_settings)
        instance = AgentOrchestrator(llm=llm, db=db, embedder=embedder)
        await instance.initialize()
        logger.info("✓ Orchestrator initialized and connected to Neo4j")
        return instance
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "unauthorized" in error_msg or "access denied" in error_msg:
            logger.error(
                f"Neo4j authentication FAILED.\n"
                f"   The password in .env does not match your Aura instance.\n"
                f"   Fix: Go to Neo4j Aura Console → {neo4j_settings.hosted_name or 'your instance'} → "
                f"Details → Security → Reset password\n"
                f"   Then update NEO4J_HOSTED_PASSWORD in .env and restart.\n"
                f"   Error: {e}"
            )
        else:
            logger.error(f"Failed to initialize orchestrator: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage orchestrator lifecycle across the app's life."""
    global _orchestrator

    load_project_env(override=False)

    neo4j_settings = Neo4jSettings()
    logger.info(f"Neo4j Target: {neo4j_settings.target}")
    logger.info(f"Connection: {neo4j_settings.connection_summary()}")

    if neo4j_settings.target == "hosted":
        if not neo4j_settings.credentials_ok_for_hosted():
            raise RuntimeError(
                f"Hosted Neo4j credentials incomplete or invalid.\n"
                f"   NEO4J_TARGET={neo4j_settings.target}\n"
                f"   NEO4J_HOSTED_NAME: {neo4j_settings.hosted_name or 'NOT SET'}\n"
                f"   NEO4J_HOSTED_PASSWORD: {'SET' if neo4j_settings.hosted_password else 'NOT SET'}\n"
                f"   NEO4J_HOSTED_URI: {neo4j_settings.hosted_uri or 'AUTO-GENERATED'}\n"
                f"\n   Fix: Ensure .env has NEO4J_TARGET=hosted, NEO4J_HOSTED_NAME, and NEO4J_HOSTED_PASSWORD\n"
                f"   Verify credentials in Neo4j Aura console → instance → copy connection details"
            )
        logger.info("Hosted Neo4j credentials configured")

    _orchestrator = await _build_orchestrator(neo4j_settings)

    yield

    if _orchestrator is not None:
        await _orchestrator.close()
        logger.info("Orchestrator closed")
    _orchestrator = None
