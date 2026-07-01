"""HTTP route handlers for the orchestrator API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from logic.orchestrator import AgentOrchestrator

from .dependencies import get_orchestrator
from .schemas import QueryRequest, QueryResponse, WriteRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.api_route("/read", methods=["GET", "POST"])
async def read(
    request: QueryRequest | None = None,
    query: str | None = None,
    top_k: int | None = None,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> QueryResponse:
    """Execute read workflow. Accepts a JSON body (POST) or query params (GET)."""
    if request is not None:
        q = request.query
        k = request.top_k
    else:
        if query is None:
            raise HTTPException(status_code=400, detail="query parameter required")
        q = query
        k = top_k

    try:
        result = await orchestrator.run_read(query=q, top_k=k)
        logger.info(f"Read result: {result}")
        return QueryResponse(data=result)
    except Exception as e:
        logger.error("Read workflow error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.api_route("/write", methods=["GET", "POST"])
async def write(
    request: WriteRequest | None = None,
    text: str | None = None,
    environment_hint: str = "general",
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> QueryResponse:
    """Execute write workflow. Accepts a JSON body (POST) or query params (GET)."""
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
