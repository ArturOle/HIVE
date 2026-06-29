import logging

from langgraph.graph import END, START, StateGraph

from src.ai.agents.reader.steps import evaluate_needs
from src.ai.agents.reader.reader_states import AdvancedReaderAgentContext, AdvancedReaderAgentState

logger = logging.getLogger(__name__)


def build_advanced_reader_graph(
    context: AdvancedReaderAgentContext
) -> StateGraph:
    target_similarity = 0.90
    adaptive_step = 10
    adaptive_cap = 120

    """Build and compile reader graph."""
 
    async def security_checks_step(state: AdvancedReaderAgentState):
        """Check the user prompt for jailbrake, prompt injection, sql injection"""
        try:
            state = await evaluate_needs(state, context)
        except Exception as e:
            logger.error(f"Error in security_checks_step: {e}")
            state.errors.append(str(e))
        return state

    async def evaluate_needs_step(state: AdvancedReaderAgentState, context: AdvancedReaderAgentContext) -> AdvancedReaderAgentState:
        """Evaluate the needs of the user based on the query and knowledge base."""
        try:
            state = await evaluate_needs(state, context)
        except Exception as e:
            logger.error(f"Error in evaluate_needs_step: {e}")
            state.errors.append(str(e))
        return state
    
    async def explore_knowledge_base_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Explore the knowledge base for relevant concepts."""
        # Placeholder for actual implementation
        return state
    
    async def write_response_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Write the final response based on the evaluated needs and explored knowledge base."""
        # Placeholder for actual implementation
        return state
    
    async def format_output_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Format the output for the user."""
        # Placeholder for actual implementation
        return state
    
    async def quality_review_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Perform a quality review of the response."""
        # Placeholder for actual implementation
        return state

    graph = StateGraph(
        state_schema=AdvancedReaderAgentState,
        context_schema=AdvancedReaderAgentContext,
    )
    graph.add_node("security_checks", security_checks_step)
    graph.add_node("evaluate_needs", evaluate_needs_step)
    graph.add_node("explore_knowledge_base", explore_knowledge_base_step)
    graph.add_node("write_response", write_response_step)
    graph.add_node("format_output", format_output_step)
    graph.add_node("quality_review", quality_review_step)
    return graph.compile()