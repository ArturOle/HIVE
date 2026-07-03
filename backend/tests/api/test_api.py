

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_orchestrator
from api.routes import router


@pytest.fixture
def mock_orchestrator() -> AsyncMock:
    """A fresh AsyncMock standing in for AgentOrchestrator on every test."""
    orchestrator = AsyncMock()
    orchestrator.run_read.return_value = {"answer": "mock read result"}
    orchestrator.run_write.return_value = {"status": "written"}
    return orchestrator


@pytest.fixture
def client(mock_orchestrator: AsyncMock) -> TestClient:
    """TestClient with the orchestrator dependency overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    return TestClient(app)


@pytest.fixture
def client_no_orchestrator() -> TestClient:
    """TestClient where the orchestrator dependency raises 503, as it does
    for real when the orchestrator hasn't finished initializing yet."""
    from fastapi import HTTPException

    def _raise_503():
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_orchestrator] = _raise_503
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_read_post_with_body(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.post("/read", json={"query": "hello", "top_k": 5})
    assert response.status_code == 200
    assert response.json() == {"data": {"answer": "mock read result"}}
    mock_orchestrator.run_read.assert_awaited_once_with(query="hello", top_k=5)


def test_read_post_body_without_top_k(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.post("/read", json={"query": "hello"})
    assert response.status_code == 200
    mock_orchestrator.run_read.assert_awaited_once_with(query="hello", top_k=None)


def test_read_get_with_query_params(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.get("/read", params={"query": "hello", "top_k": 3})
    assert response.status_code == 200
    assert response.json() == {"data": {"answer": "mock read result"}}
    mock_orchestrator.run_read.assert_awaited_once_with(query="hello", top_k=3)


def test_read_get_without_query_param_is_400(client: TestClient) -> None:
    response = client.get("/read")
    assert response.status_code == 400


def test_read_orchestrator_error_is_500(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    mock_orchestrator.run_read.side_effect = RuntimeError("boom")
    response = client.post("/read", json={"query": "hello"})
    assert response.status_code == 500
    assert "boom" in response.json()["detail"]


def test_read_service_unavailable_when_not_initialized(client_no_orchestrator: TestClient) -> None:
    response = client_no_orchestrator.post("/read", json={"query": "hello"})
    assert response.status_code == 503


def test_write_post_with_body(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.post("/write", json={"text": "some fact", "environment_hint": "kitchen"})
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "written"}}
    mock_orchestrator.run_write.assert_awaited_once_with(text="some fact", environment_hint="kitchen")


def test_write_post_body_defaults_environment_hint(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.post("/write", json={"text": "some fact"})
    assert response.status_code == 200
    mock_orchestrator.run_write.assert_awaited_once_with(text="some fact", environment_hint="general")


def test_write_get_with_query_params(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    response = client.get("/write", params={"text": "some fact", "environment_hint": "garage"})
    assert response.status_code == 200
    mock_orchestrator.run_write.assert_awaited_once_with(text="some fact", environment_hint="garage")


def test_write_get_without_text_param_is_400(client: TestClient) -> None:
    response = client.get("/write")
    assert response.status_code == 400


def test_write_orchestrator_error_is_500(client: TestClient, mock_orchestrator: AsyncMock) -> None:
    mock_orchestrator.run_write.side_effect = RuntimeError("kaboom")
    response = client.post("/write", json={"text": "some fact"})
    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]


def test_write_service_unavailable_when_not_initialized(client_no_orchestrator: TestClient) -> None:
    response = client_no_orchestrator.post("/write", json={"text": "some fact"})
    assert response.status_code == 503
