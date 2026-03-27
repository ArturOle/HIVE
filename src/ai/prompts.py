
PROBLEM_DEFINITION = """
A Problem is a specific tension or discrepancy between the Current State of an environment and a Desired State, where the environments existing constraints prevent an easy transition from one to the other.
Environmental Context: A problem doesn't exist in a vacuum. For example, "it's raining" is not a problem for a fish; it's only a problem for a human trying to stay dry. The environment dictates whether a circumstance is a "feature" or a "bug."
Reasoning Lead: To define a problem, you must identify the constraint. Ask: "What specific environmental factor (lack of money, time, physics, or social norms) is keeping us from the goal?"
"""

SOLUTION_DEFINITION = """
A Solution is a targeted set of actions or changes designed to navigate or alter environmental constraints to bridge the gap between the current state and the desired state.
Environmental Context: A solution must be viable within the environment. If you propose a high-tech digital app to solve a communication problem in a region without electricity, you haven't designed a solution; you've designed a fantasy. A true solution respects the resource limits and "physics" of its surroundings.
Reasoning Lead: A solution is essentially a hypothesis. It says, "Given these environmental rules, if we apply X force at Y point, the friction should decrease."
"""

RESULT_DEFINITION = """
The Result is the measurable and qualitative shift in the environment following the implementation of a solution, encompassing both the intended outcomes and the unintended ripple effects.
Environmental Context: Every action has a reaction. The "Result" isn't just "The problem is gone." It's the new environment created by the solution. Sometimes a solution fixes one problem but creates a "Side-Effect Problem" (e.g., a medicine that cures a cough but makes you drowsy).
Reasoning Lead: Results provide the feedback loop. You compare the Result back to the original Problem. If the friction still exists—or if the environment has become more unstable—the reasoning process begins again.
"""

WRITER_DISCOVERY_PROMPT = """
Your role is to extract the problem, solution, and result given presented enviroment from the text into a structured JSON object.
Here are definitions of the problem, solution, and result:
{problem_definition}
{solution_definition}
{result_definition}

Here is the enviroment:
{enviroment}

The JSON object should have the following structure:
{
    "environment": "The constraints, rules, and context of the situation, topic and theme.",
    "problem": "The specific tension/gap identified.",
    "solution": "The action taken.",
    "mechanism": "Why this specific solution was expected to overcome the environmental constraints.",
    "result": "The measurable outcome and any ripple effects."
}

The text to analyze is:
{text}
"""


WRITER_REFLECTION_PROMPT = """
Your role is to reflect if solution for the problem in given enviroment and grade it from 0.0 to 5.0 based on the result.

Grading scale:
0 - solution made the problem worse.
1 - solution did not solve the problem.
2 - solution solved the problem with high amount of effort, cost, time and level of complexity.
3 - solution solved the problem, but with additional effort, cost, time and moderate level of complexity.
4 - solution solved the problem with no downside.
5 - solution solved the problem, increased efficiency, effectiveness, productivity, etc. and/or solved additional problems.

Problem:
{problem}

Solution:
{solution}

Result:
{result}

Enviroment:
{enviroment}

Result should be a structured JSON object with the following structure:
{
    "grade": 0.0,
    "reasoning": "Detailed justification of the grade based on efficiency and side effects.",
    "key_lesson": "The 'heuristic' or rule of thumb learned from this experience.",
    "risk_factors": "What environmental changes would degrade the solution's grade?"
}
"""
