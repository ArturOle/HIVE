from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.submitter import build_submitter_graph


@pytest.mark.asyncio
async def test_submitter_discovery_handles_empty_llm_output():
    class EmptyLLM:
        async def ainvoke(self, prompt: str):
            return ""

    graph = build_submitter_graph(
        db=MagicMock(),
        llm=EmptyLLM(),
        embedder=MagicMock(),
    )

    result = await graph.ainvoke({"text": "some text", "environment_hint": "auto", "errors": []})

    assert "errors" in result
    assert any("Model output is empty" in err for err in result["errors"])
    assert any("Discovery node failed to parse" in err for err in result["errors"])


@pytest.mark.asyncio
async def test_submitter_discovery_handles_malformed_llm_output():
    class BadLLM:
        async def ainvoke(self, prompt: str):
            return "Not a json payload"

    graph = build_submitter_graph(
        db=MagicMock(),
        llm=BadLLM(),
        embedder=MagicMock(),
    )

    result = await graph.ainvoke({"text": "some text", "environment_hint": "auto", "errors": []})

    assert "errors" in result
    assert any("does not contain valid JSON payload" in err or "Discovery node failed to parse" in err for err in result["errors"])
