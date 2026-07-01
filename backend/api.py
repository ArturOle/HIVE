"""FastAPI server entrypoint for the orchestrator."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from api.dependencies import lifespan
from api.routes import router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(lifespan=lifespan, title="HIVE Orchestrator API")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
