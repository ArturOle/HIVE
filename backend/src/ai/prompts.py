"""Prompt contracts shared by writer and reader agents."""

CONCEPT_KEYS = ("environment", "problem", "solution", "mechanism", "result")

ENVIRONMENT_DEFINITION = """
An environment is all relevant prior knowledge and contextual backdrop for a
situation—the where, when, who, prior state, and conditions that existed
before the problem occurred. It is background, not the problem itself: it
establishes what was already true or known, within which a problem later
emerged and a solution had to operate. Environment is broader than
"constraints"—it includes any prior fact, setting, or state that shaped what
happened next, whether or not it acted as a limitation.
"""

PROBLEM_DEFINITION = """
A problem is the event, trigger, or issue that initiated the situation—
something that happened, was noticed, or went wrong within the environment,
prompting a response. Describe the concrete triggering event or issue itself
("symptoms worsened after starting X"), not an abstract description of a gap
between states ("suboptimal control was present").
"""

SOLUTION_DEFINITION = """
A solution is a targeted action set that works within the environment
to respond to the problem event and move toward a desired state.
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
- If `environment` is empty, generic, or not explicitly provided, infer it from
  ALL relevant prior/background knowledge present in the text—not just explicit
  constraints.
- Capture the full contextual backdrop: where, when, who/what system, prior
  state, and any conditions that existed before the problem occurred.
- Infer only the local context relevant to each extracted problem/solution/result;
  ignore unrelated sections; select only environments tied to specific tips/cases.
- When multiple extracted concepts share the same backdrop, reuse identical
  environment phrasing across them rather than rewording it independently each
  time—this keeps equivalent environments mergeable downstream.
- Environment may include domain artifacts (device type, runtime/language,
  identifiers, operating conditions, constraints, and usage history), but is not
  limited to constraints alone—background facts, prior state, and setting all
  count as environment.

Problem extraction rules:
- Treat each problem as a concrete triggering event or issue—something that
  happened, was noticed, or went wrong—not an abstract statement of a gap
  between states.
- Prefer the language of "what occurred" over "what is missing."

IMPORTANT: Extract MULTIPLE concepts if present. Return as many valid concept
objects as you find.

Return ONLY valid JSON with this exact shape:
[
  {{
    "environment": "prior knowledge and contextual backdrop",
    "problem": "the triggering event or issue",
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
You evaluate whether the solution resolved the problem event in the environment.
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

Definitions:
{problem_definition}
{solution_definition}
{result_definition}
{environment_definition}
{mechanism_definition}

Extraction rules:
- environment: prior knowledge/background the user stated (where, when, who,
  prior state, conditions)—not the triggering event itself.
- problem: the concrete triggering event or issue the user described—not an
  abstract gap they didn't actually state.
- Only fill a field if the user's query actually contains that information;
  do not infer or supply facts the user didn't provide. Use null otherwise.

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
- environment: the prior knowledge and contextual backdrop under which the concept applies
- problem: the triggering event or issue the concept addresses
- solution: the action taken to respond to the problem
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
  weights reflect how strongly each should constrain graph traversal, independently from 1 to 10.
  Only include a value if it is actually present in the user's query text — never supply outside
  knowledge. environment values are prior knowledge/background the user stated (where, when, who,
  prior state); problem values are the triggering event or issue the user described, not an inferred gap.
- reasoning: one sentence explaining the retrieval decision and intent classification

Return ONLY valid JSON with this exact shape:
{{
  "reasoning": "string",
  "primary_intent": {{"field": "one of: environment, problem, solution, mechanism, result", "weight": 0.0}},
  "additional_concepts": {{
    "environment": [{{"value": "string or null", "weight": 0}}],
    "problem": [{{"value": "string or null", "weight": 0}}],
    "solution": [{{"value": "string or null", "weight": 0}}],
    "mechanism": [{{"value": "string or null", "weight": 0}}],
    "result": [{{"value": "string or null", "weight": 0}}]
  }}
}}
"""