"""Writer agent LangGraph workflow for storing knowledge in Neo4j."""

from __future__ import annotations

import json
import re
import logging
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator

PATTERN_FINDER_AGENT_PROMPT = """
Extract the high quality regex patterns for hierarchical divisions of the provided document.
The divisions that can apear in the provided text are provided in the table below.

depth	Depth name	Common Names in Different Domains	Typical Numbering / ID Method
1	Volume	Volume, Tome, Book (when a work is split)	"Volume I", "Vol. A"
2	Part	Part, Unit, Division, Book (in multi-book volumes), Act (drama)	"Part 1", "Part A"
3	Chapter	Chapter, Module, Lesson (educational), Clause (in some standards)	"Chapter 1", "1."
4	Section	Section, Major Section, Heading-1	"1.1", "§1", "Section 1"
5	Subsection	Subsection, Sub-section, Heading-2, Clause (sometimes)	"1.1.1", "1.1(a)"
6	Sub-subsection	Sub-subsection, Heading-3, Subclause (standards), Article (treaties)	"1.1.1.1", "1.1.1.1.1"
7	Paragraph	Paragraph, para, ¶, Level-4 heading, Clause (legal)	"(1)", "(a)", "[1.1.1.1.1]"
8	Subparagraph	Subparagraph, Sub-para, Item (legal), Subclause (when nested deeply)	"(A)", "(i)", "(I)"
9	Clause / Item	Clause, Item, Indent, List element, bullet point (in unstructured text)	"(aa)", "●", "a."

The extracted patterns should be in the form of dictionary where each division pattern is an object with the following structure:
[
    {
        "depth": <number>, // The hierarchical level (1-9)
        "depth_name": <string>, // The name of the depth level (e.g., "Volume", "Part", "Chapter", etc.)
        "regex_pattern": <string> // The regex pattern prepared to extract the division preapared for the provided text. It should be a regex working for the entire document.
    }
]

The example output:
[
    {
        "depth": 4,
        "depth_name": "Section",
        "regex_pattern": <regex pattern here>
    },
    {
        "depth": 5,
        "depth_name": "Subsection",
        "regex_pattern": <regex pattern here>
    },
    ...
]

The regex should be constructed to not match mentions of given section or entry in table of contents, index, or references to other sections. It should only match the actual section headers in the main body of the text.
If a certain level is not present in the provided text, omit. Prepare only patterns for the levels that are present in the provided text.
Here is the text to analyze:

"""

logger = logging.getLogger(__name__)


def parse_json_block(text: str):
    """
    Parses a string containing a markdown-fenced JSON block
    (e.g. '```json\\n...\\n```') into a Python object (list/dict).
    """
    # Remove ```json ... ``` or ``` ... ``` fences if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    json_str = match.group(1) if match else text.strip()

    return json.loads(json_str)

class LLMClient(Protocol):
    """Abstract language model client for text generation."""

    async def ainvoke(self, prompt: str) -> str:
        """Generate a response from a prompt."""


class EmbedderClient(Protocol):
    """Abstract embedder client for vector embeddings."""

    async def embed(self, text: str) -> list[float]:
        """Create a vector representation of text."""


class ExtractedPattern(BaseModel):
    """Validated extraction contract for graph persistence."""

    level: int = Field(ge=1, le=9)
    level_name: str
    regex_pattern: str

    @field_validator("regex_pattern", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> str:
        """Convert list or other types to string for all fields."""
        if isinstance(v, str):
            return v
        return str(v)

class PatternFinderState(TypedDict, total=False):
    """LangGraph state for pattern finder pipeline."""

    text: str
    page_number: int | None
    patterns: list[ExtractedPattern] | list | None
    errors: list[str]



def _extract_json_object(raw: str) -> dict[str, Any]:
    """Extract first JSON object from model output."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output does not contain valid JSON object")
        return json.loads(raw[start : end + 1])


def build_pattern_finder_graph(
    llm: LLMClient | None = None,
) -> StateGraph[PatternFinderState]:
    """Build and compile pattern finder graph."""

    async def pattern_finder_node(state: PatternFinderState) -> PatternFinderState:
        text = state.get("text", "").strip()
        errors = list(state.get("errors", []))
        if not text:
            errors.append("Writer input text is empty.")
            return {"errors": errors}

        prompt = PATTERN_FINDER_AGENT_PROMPT + f"\n\n{text[24000:]}"
        raw = await llm.ainvoke(prompt)

        # Parse as JSON array
        raw_data = parse_json_block(raw)
        
        return PatternFinderState(
            patterns=[ExtractedPattern(
                level=item.get("depth"),
                level_name=item.get("depth_name"),
                regex_pattern=item.get("regex_pattern", "")
            ) for item in raw_data],
            errors=errors,
        )

    graph = StateGraph(PatternFinderState)
    graph.add_node("pattern_finder", pattern_finder_node)
    graph.add_edge(START, "pattern_finder")
    graph.add_edge("pattern_finder", END)
    return graph.compile()


if __name__ == "__main__":
    from src.ai.providers.inception import InceptionLLMClient, InceptionProviderConfig
    llm_config = InceptionProviderConfig()
    llm_node = InceptionLLMClient(
        config=llm_config
    )
    graph = build_pattern_finder_graph(llm=llm_node)

    # Example usage
    text = ""
    with open("/home/r2/Documents/Projects/ReLived/backend/data_cold/eu_gdpr.txt", "r") as f:
        text = f.read()
    
    initial_state: PatternFinderState = {"text": text}
    result = graph.run(initial_state)
    print(result)