"""Prompt contracts shared by writer and reader agents."""

CONCEPT_KEYS = ("environment", "problem", "solution", "mechanism", "result")

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

"""

REFLECTION_DEFINITION = """

"""

WRITER_DISCOVERY_PROMPT = """
You extract ALL distinct knowledge concepts from text into a JSON array.
Extract as many environment-problem-solution-result quadruples as you can find.

Definitions:
{problem_definition}
{solution_definition}
{result_definition}

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
