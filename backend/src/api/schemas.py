"""Pydantic request/response models for the orchestrator API."""

from __future__ import annotations

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Read query request."""

    query: str
    top_k: int | None = None


class WriteRequest(BaseModel):
    """Write request."""

    text: str
    environment_hint: str = "general"


class QueryResponse(BaseModel):
    """Read/write query response."""

    data: dict
