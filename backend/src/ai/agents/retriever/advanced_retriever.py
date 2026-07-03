import logging

from langgraph.graph import END, START, StateGraph

from ai.agents.retriever.steps import evaluate_needs, explore_knowledge
from ai.agents.retriever.models import AdvancedAgentContext, AdvancedReaderAgentState

logger = logging.getLogger(__name__)


def build_advanced_retriever_graph(
    context: AdvancedAgentContext
) -> StateGraph:
    target_similarity = 0.90
    adaptive_step = 10
    adaptive_cap = 120

    """Build and compile reader graph."""
 
    async def security_checks_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Check the user prompt for jailbrake, prompt injection, sql injection"""
        try:
            state = await evaluate_needs(state, context)
        except Exception as e:
            logger.error(f"Error in security_checks_step: {e}")
            state.errors.append(str(e))
        return state

    async def evaluate_needs_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Evaluate the needs of the user based on the query and knowledge base."""
        try:
            return await evaluate_needs(state, context)
            
        except Exception as e:
            logger.error(f"Error in evaluate_needs_step: {e}")
            state.errors.append(str(e))
            return state
    
    async def explore_knowledge_base_step(state: AdvancedReaderAgentState) -> AdvancedReaderAgentState:
        """Explore the knowledge base for relevant concepts."""
        try:
            update = await explore_knowledge(state, context)
            merged = state.model_copy(deep=True)
            for key, value in update.items():
                if key == "errors":
                    merged.errors = list(merged.errors) + list(value)
                else:
                    setattr(merged, key, value)
            return merged
        except Exception as e:
            logger.error(f"Error in explore_knowledge_base_step: {e}")
            state.errors.append(str(e))
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
        context_schema=AdvancedAgentContext,
    )
    # TODO: <maybe not here but still> graph.add_node("security_checks", security_checks_step)
    graph.add_node("evaluate_needs", evaluate_needs_step)
    graph.add_node("explore_knowledge_base", explore_knowledge_base_step)
    graph.add_node("write_response", write_response_step)
    graph.add_node("format_output", format_output_step)
    graph.add_node("quality_review", quality_review_step)

    graph.add_edge(START, "evaluate_needs")
    graph.add_edge("evaluate_needs", "explore_knowledge_base")
    graph.add_edge("explore_knowledge_base", "write_response")
    graph.add_edge("write_response", "format_output")
    graph.add_edge("format_output", "quality_review")
    graph.add_edge("quality_review", END)
    
    return graph.compile()