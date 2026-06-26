"""Prompt contracts shared by writer and reader agents."""

CONCEPT_KEYS = ("environment", "problem", "solution", "mechanism", "result")

ENVIRONMENT_DEFINITION = """
An environment is the foundational context—comprising rules, constraints, conditions, and domain artifacts—that dictates the boundaries within which a problem exists and a solution must operate.
"""

PROBLEM_DEFINITION = """
A problem is a specific tension between the current state and a desired state,
where environmental constraints prevent an easy transition.
"""

SOLUTION_DEFINITION = """
A solution is a targeted action set that works within environmental constraints
to bridge the gap between current and desired states.
"""

RESULT_DEFINITION = """
A result is the measurable and qualitative shift after a solution is applied,
including both intended outcomes and unintended side effects.
"""

MECHANISM_DEFINITION = """
A mechanism is the reasoning behind the solution, an intuitive hypothesis of how the solution should work under the environment.
"""

REFLECTION_DEFINITION = """
A reflection is the evaluation of the mechanism against the result, a retrospective understanding of what went well and what could be improved.
"""

WRITER_DISCOVERY_PROMPT = """
You extract ALL distinct knowledge concepts from text into a JSON array.
Extract as many environment-problem-solution-result quadruples as you can find.
If there is important information but lacks some concepts, keep.

Definitions:
{problem_definition}
{solution_definition}
{result_definition}
{environment_definition}

Environment context hint:
{environment}

Environment deduction rules:
- If `environment` is empty, generic, or not explicitly provided, infer it from the text.
- Infer only the local context relevant to each extracted problem/solution/result.
- Ignore unrelated sections; select only environments tied to specific tips/cases.
- Environment may include domain artifacts (device type, runtime/language, identifiers,
  operating conditions, constraints, and usage history) when relevant.

IMPORTANT: Extract MULTIPLE concepts if present. Return as many valid concept objects as you find.

Return ONLY valid JSON with this exact shape:
[
  {{
    "environment": "constraints, rules, and context",
    "problem": "the tension or gap",
    "solution": "the action taken",
    "mechanism": "why this should work under the environment",
    "result": "observed outcome and ripple effects"
  }},
  {{
    "environment": "...",
    "problem": "...",
    "solution": "...",
    "mechanism": "...",
    "result": "..."
  }}
]

Text:
{text}
"""

WRITER_REFLECTION_PROMPT = """
You evaluate whether the solution resolved the problem in the environment.
Grade from 0.0 to 5.0 based on result quality.

Grading scale:
0: solution made the problem worse
1: solution did not solve the problem
2: solved with high effort/cost/complexity
3: solved with moderate overhead
4: solved with no meaningful downside
5: solved and improved efficiency/effectiveness or solved additional problems

Problem:
{problem}

Solution:
{solution}

Mechanism:
{mechanism}

Result:
{result}

Environment:
{environment}

Return ONLY valid JSON with this exact shape:
{{
  "grade": 0.0,
  "reasoning": "detailed justification",
  "key_lesson": "portable heuristic learned",
  "risk_factors": "environmental changes that may degrade results"
}}
"""

READER_CONCEPT_PARSE_PROMPT = """
Extract any available concept fragments from the user query.
Use null when a concept is missing.

Return ONLY valid JSON with this exact shape:
{{
  "environment": "string or null",
  "problem": "string or null",
  "solution": "string or null",
  "mechanism": "string or null",
  "result": "string or null"
}}

User query:
{query}
"""

COMPOSE_RESPONSE_PROMPT = """
You synthesize retrieved knowledge concepts into a clear, grounded response to the user's query.

Your response must be:
- Directly answering the query using only the evidence provided
- Traceable: every claim should map to a ranked concept
- Honest about uncertainty when ranked concepts are a weak match
- Concise but complete — do not pad, do not omit critical nuance

Concept fields for reference:
- environment: the constraints and context under which the knowledge applies
- problem: the tension or gap the concept addresses
- solution: the action taken to resolve the problem
- mechanism: the reasoning for why the solution works in that environment
- result: observed outcomes and side effects after the solution was applied

Grading scale used to score ranked concepts (higher = more reliable):
0: solution made the problem worse
1: solution did not solve the problem
2: solved with high effort/cost/complexity
3: solved with moderate overhead
4: solved with no meaningful downside
5: solved and improved efficiency/effectiveness or solved additional problems

Composition rules:
- Prioritize concepts with higher grades; treat grade < 2 as cautionary evidence only
- If the query matches multiple ranked concepts, synthesize across them — do not just list
- If ranked concepts do not address the query, say so explicitly rather than hallucinating
- Reference alternatives only when they offer meaningfully different approaches or environments
- Preserve environmental specificity: a solution that worked in one environment may not transfer

User query:
{query}

Ranked concepts (ordered by relevance and grade):
{ranked}

Alternative concepts (lower relevance, included for breadth):
{alternatives}

Return ONLY valid JSON with this exact shape:
{{
  "response": "direct, synthesized answer to the query",
  "confidence": "high | medium | low",
  "confidence_reasoning": "why the ranked evidence does or does not strongly support this answer",
  "applied_concepts": ["short label for each ranked concept actually used"],
  "caveats": "environmental limits, grade penalties, or transfer risks the user should know — null if none"
}}
"""

EVALUATE_NEEDS_PROMPT = """
You analyze a user query against a knowledge base of environment-problem-solution-result concepts.

Concept fields:
environment - {environment}
problem - {problem}
solution - {solution}
mechanism - {mechanism}
result - {result}

User query:
{query}

Definitions:
- primary_intent: the concept field(s) the user most wants to discover, each with a weight reflecting
  relative importance
- additional_concepts: all other concept fields recognized in the query with their values and weights;
  weights reflect how strongly each should constrain graph traversal, independently from 1 to 10
- reasoning: one sentence explaining the retrieval decision and intent classification

Return ONLY valid JSON with this exact shape:
{{
  "reasoning": "string",
  "primary_intent": [
    {{"field": "one of: environment, problem, solution, mechanism, result", "weight": 0.0}}
  ],
  "additional_concepts": {{
    "environment": [{{"value": "string or null", "weight": 0.0}}],
    "problem": [{{"value": "string or null", "weight": 0.0}}]
    "solution": [{{"value": "string or null", "weight": 0.0}}],
    "mechanism": [{{"value": "string or null", "weight": 0.0}}],
    "result": [{{"value": "string or null", "weight": 0.0}}]
  }}
}}
"""
