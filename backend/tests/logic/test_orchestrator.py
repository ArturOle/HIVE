

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust this import to match your project's structure
from logic.orchestrator import AgentOrchestrator

@pytest.fixture
def mock_db():
    """Provides a mocked DatabaseManager."""
    db = MagicMock()
    db.initialize = AsyncMock()
    db.setup_database = AsyncMock()
    db.close = AsyncMock()
    return db

@pytest.fixture
def mock_llm():
    """Provides a mocked LLM Client."""
    return MagicMock()

@pytest.fixture
def mock_embedder():
    """Provides a mocked Embedder Client."""
    return MagicMock()

@pytest.fixture
def orchestrator(mock_db, mock_llm, mock_embedder):
    """Provides a fresh, uninitialized orchestrator instance."""
    return AgentOrchestrator(
        db=mock_db,
        llm=mock_llm,
        embedder=mock_embedder,
        top_k=5
    )

@pytest.mark.asyncio
@patch("logic.orchestrator.build_submitter_graph")
@patch("logic.orchestrator.build_retriever_graph")
@patch("logic.orchestrator.build_advanced_retriever_graph")
async def test_initialize(
    mock_build_advanced, mock_build_retrieve, mock_build_submit, orchestrator, mock_db
):
    """Test that initialization sets up the DB and compiles the graphs correctly."""
    await orchestrator.initialize()

    # Verify DB methods were called
    mock_db.initialize.assert_awaited_once()
    mock_db.setup_database.assert_awaited_once()

    # Verify graph builders were called
    mock_build_submit.assert_called_once_with(
        db=orchestrator.context.db,
        llm=orchestrator.context.llm,
        embedder=orchestrator.context.embedder
    )
    mock_build_retrieve.assert_called_once_with(
        db=orchestrator.context.db,
        llm=orchestrator.context.llm,
        embedder=orchestrator.context.embedder
    )
    mock_build_advanced.assert_called_once_with(
        context=orchestrator.context
    )

    # Verify state changes
    assert orchestrator._initialized is True
    assert orchestrator.submit_graph == mock_build_submit.return_value
    assert orchestrator.retrieve_graph == mock_build_retrieve.return_value
    assert orchestrator.advanced_retrieve_graph == mock_build_advanced.return_value

@pytest.mark.asyncio
async def test_uninitialized_execution_raises_error(orchestrator):
    """Ensure running graphs before initialization raises a RuntimeError."""
    with pytest.raises(RuntimeError, match="Orchestrator not initialized"):
        await orchestrator.run_submit("Test text")

    with pytest.raises(RuntimeError, match="Orchestrator not initialized"):
        await orchestrator.run_retrieve("Test query")

    with pytest.raises(RuntimeError, match="Orchestrator not initialized"):
        await orchestrator.run_advanced_retrieve("Test query")

@pytest.mark.asyncio
async def test_run_submit(orchestrator):
    """Test standard submit execution delegates to the submit graph."""
    # Mock initialized state
    orchestrator.submit_graph = MagicMock()
    orchestrator.submit_graph.ainvoke = AsyncMock(return_value={"status": "success"})
    orchestrator._initialized = True

    result = await orchestrator.run_submit("New entry", "dev")
    
    orchestrator.submit_graph.ainvoke.assert_awaited_once_with({
        "text": "New entry",
        "environment_hint": "dev",
        "errors": []
    })
    assert result == {"status": "success"}

@pytest.mark.asyncio
async def test_run_retrieve(orchestrator):
    """Test retrieve execution uses default or provided top_k."""
    # Mock initialized state
    orchestrator.retrieve_graph = MagicMock()
    orchestrator.retrieve_graph.ainvoke = AsyncMock(return_value={"results": []})
    orchestrator._initialized = True

    # Test with default top_k
    result = await orchestrator.run_retrieve("Find this")
    orchestrator.retrieve_graph.ainvoke.assert_awaited_with({
        "query": "Find this",
        "top_k": 5, # default from fixture
        "errors": []
    })
    assert result == {"results": []}

    # Test with overridden top_k
    await orchestrator.run_retrieve("Find this", top_k=10)
    orchestrator.retrieve_graph.ainvoke.assert_awaited_with({
        "query": "Find this",
        "top_k": 10,
        "errors": []
    })

@pytest.mark.asyncio
async def test_run_router(orchestrator):
    """Test the general run() method accurately routes requests."""
    orchestrator.run_submit = AsyncMock(return_value={"routed": "submit"})
    orchestrator.run_retrieve = AsyncMock(return_value={"routed": "retrieve"})
    orchestrator.run_advanced_retrieve = AsyncMock(return_value={"routed": "advanced"})

    # Test Submit Route
    res = await orchestrator.run(mode="submit", text="Text")
    assert res == {"routed": "submit"}
    orchestrator.run_submit.assert_awaited_once_with(text="Text", environment_hint="general")

    # Test Retrieve Route
    res = await orchestrator.run(mode=" RETRIEVE ", text="Query", top_k=3)
    assert res == {"routed": "retrieve"}
    orchestrator.run_retrieve.assert_awaited_once_with(query="Query", top_k=3)

    # Test Advanced Route
    res = await orchestrator.run(mode="advanced_retrieve", text="Query")
    assert res == {"routed": "advanced"}
    orchestrator.run_advanced_retrieve.assert_awaited_once_with(query="Query", top_k=None)

    # Test Invalid Route
    with pytest.raises(ValueError, match="Mode must be either"):
        await orchestrator.run(mode="invalid_mode", text="Text")

@pytest.mark.asyncio
async def test_context_manager(orchestrator, mock_db):
    """Test __aenter__ and __aexit__ properly initialize and close resources."""
    # We patch initialization so we don't need real graph builders for this test
    with patch.object(orchestrator, 'initialize', new_callable=AsyncMock) as mock_init:
        async with orchestrator as context_orch:
            assert context_orch == orchestrator
            mock_init.assert_awaited_once()

        mock_db.close.assert_awaited_once()
        assert orchestrator._initialized is False