from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ai.agents.retriever.advanced_retriever import build_advanced_retriever_graph
from ai.agents.retriever.models import AdvancedAgentContext, AdvancedReaderAgentState
from ai.agents.retriever.steps.explore_knowledge import explore_knowledge


def test_advanced_reader_state_accepts_minimal_initial_input():
    state = AdvancedReaderAgentState(query="What causes fever?", top_k=5, errors=[])

    assert state.query == "What causes fever?"
    assert state.top_k == 5
    assert state.query_embedding == []
    assert state.search_target is None
    assert state.errors == []


@pytest.mark.asyncio
async def test_advanced_retriever_graph_can_invoke_with_minimal_state():
    class DummyLLM:
        async def ainvoke(self, prompt: str):
            return '{"reasoning": "test", "primary_intent": {"problem": "fever"}, "additional_concepts": {"problem": [{"value": "fever", "weight": 5}]}}'

    class DummyEmbedder:
        async def embed(self, text: str):
            return [0.1, 0.2]

    class DummyDB:
        async def search_concept_nodes(self, label: str, embedding: list[float], top_k: int):
            return [{"node_id": "1", "text": "fever", "similarity": 0.95}]

    context = AdvancedAgentContext(
        db=DummyDB(),
        llm=DummyLLM(),
        embedder=DummyEmbedder(),
    )
    graph = build_advanced_retriever_graph(context)

    result = await graph.ainvoke({"query": "What causes fever?", "errors": []})

    assert result["errors"] == []


@pytest.mark.asyncio
async def test_explore_knowledge_queries_relevant_concepts_and_stores_results():
    db = SimpleNamespace(
        search_concept_nodes=AsyncMock(
            return_value=[{"node_id": "1", "text": "Memory concept", "similarity": 0.91}]
        )
    )
    state = {
        "query_embedding": [0.1, 0.2],
        "top_k": 2,
        "errors": [],
        "search_target": "problem",
        "concepts_from_query": {
            "problem": [{"value": "memory", "weight": 5}],
        },
    }
    context = SimpleNamespace(db=db, errors=[])

    result = await explore_knowledge(state, context)

    db.search_concept_nodes.assert_awaited_once_with(
        label="Problem",
        embedding=[0.1, 0.2],
        top_k=2,
    )
    assert result["errors"] == []
    assert result["concepts_from_knowledge_base"]["problem"][0]["text"] == "Memory concept"
