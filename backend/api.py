"""FastAPI server for the orchestrator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from src.ai.providers.qwen import QwenEmbedderClient, QwenProviderConfig, QwenLLMClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.logic.orchestrator import AgentOrchestrator
from src.database.config import Neo4jSettings, load_project_env
from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: AgentOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage orchestrator lifecycle."""
    global orchestrator
    # Startup
    load_project_env(override=False)
    
    # Load settings (respects NEO4J_TARGET for hosted/local/docker)
    neo4j_settings = Neo4jSettings()
    
    logger.info(f"Neo4j Target: {neo4j_settings.target}")
    logger.info(f"Connection: {neo4j_settings.connection_summary()}")
    
    if neo4j_settings.target == "hosted":
        if not neo4j_settings.credentials_ok_for_hosted():
            raise RuntimeError(
                f"❌ Hosted Neo4j credentials incomplete or invalid.\n"
                f"   NEO4J_TARGET={neo4j_settings.target}\n"
                f"   NEO4J_HOSTED_NAME: {neo4j_settings.hosted_name or 'NOT SET'}\n"
                f"   NEO4J_HOSTED_PASSWORD: {'SET' if neo4j_settings.hosted_password else 'NOT SET'}\n"
                f"   NEO4J_HOSTED_URI: {neo4j_settings.hosted_uri or 'AUTO-GENERATED'}\n"
                f"\n   Fix: Ensure .env has NEO4J_TARGET=hosted, NEO4J_HOSTED_NAME, and NEO4J_HOSTED_PASSWORD\n"
                f"   Verify credentials in Neo4j Aura console → instance → copy connection details"
            )
        logger.info(f"✓ Hosted Neo4j credentials configured")
    
    try:
        cfg = QwenProviderConfig()
        llm = QwenLLMClient(cfg)
        emb_cfg = QwenProviderConfig()
        embedder = QwenEmbedderClient(emb_cfg)
        db = DatabaseManager(settings=neo4j_settings)
        orchestrator = AgentOrchestrator(llm=llm, db=db, embedder=embedder)
        await orchestrator.initialize()
        logger.info("✓ Orchestrator initialized and connected to Neo4j")
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "unauthorized" in error_msg or "access denied" in error_msg:
            logger.error(
                f"❌ Neo4j authentication FAILED.\n"
                f"   The password in .env does not match your Aura instance.\n"
                f"   Fix: Go to Neo4j Aura Console → {neo4j_settings.hosted_name or 'your instance'} → "
                f"Details → Security → Reset password\n"
                f"   Then update NEO4J_HOSTED_PASSWORD in .env and restart.\n"
                f"   Error: {e}"
            )
        else:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
        raise
    
    yield
    # Shutdown
    await orchestrator.close()
    logger.info("Orchestrator closed")


app = FastAPI(lifespan=lifespan, title="ReLived Orchestrator API")


class QueryRequest(BaseModel):
    """Read query request."""
    query: str
    top_k: int | None = None


class WriteRequest(BaseModel):
    """Write request."""
    text: str
    environment_hint: str = "general"


class QueryResponse(BaseModel):
    """Read query response."""
    data: dict


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.api_route("/read", methods=["GET", "POST"])
async def read(request: QueryRequest | None = None, query: str | None = None, top_k: int | None = None) -> QueryResponse:
    """Execute read workflow."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    logging.info(f"Request object: {request}")
    # Handle both POST (request body) and GET (query params)

    q = request.query
    k = request.top_k

    try:
        result = await orchestrator.run_read(query=q, top_k=k)
        logging.info(f"Read result: {result}")
        return QueryResponse(data=result)
    except Exception as e:
        logger.error("Read workflow error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.api_route("/write", methods=["GET", "POST"])
async def write(request: WriteRequest | None = None, text: str | None = None, environment_hint: str = "general") -> QueryResponse:
    """Execute write workflow."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    # Handle both POST (request body) and GET (query params)
    if request is not None:
        t = request.text
        env = request.environment_hint
    else:
        if text is None:
            raise HTTPException(status_code=400, detail="text parameter required")
        t = text
        env = environment_hint
    
    try:
        result = await orchestrator.run_write(text=t, environment_hint=env)
        return QueryResponse(data=result)
    except Exception as e:
        logger.error("Write workflow error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
