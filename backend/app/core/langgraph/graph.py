"""
LangGraph Agent Definition
Orchestrates tool selection, validation, RAG routing, and error handling
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from app.core.langgraph.state import AgentState
from app.core.langgraph.nodes import (
    classify_intent_node,
    validation_node,
    force_validate_node,
    delete_document_node,
    export_invoices_node,
    rag_query_node,
    list_documents_node,
    get_details_node,
    general_chat_node,
    fallback_node,
    response_node
)

logger = logging.getLogger(__name__)


def route_by_intent(state: AgentState) -> Literal[
    "validation",
    "force_validate",
    "delete_document",
    "export_invoices",
    "rag_query",
    "list_documents",
    "get_details",
    "general_chat",
    "fallback"
]:
    """Route to appropriate node based on classified intent"""
    
    if state.error or state.needs_clarification:
        return "fallback"
    
    intent_to_node = {
        "validate_invoice": "validation",
        "force_validate": "force_validate",
        "delete_document": "delete_document",
        "export_invoices": "export_invoices",
        "query_document": "rag_query",
        "list_documents": "list_documents",
        "get_document_details": "get_details",
        "general_chat": "general_chat",
        "unclear": "fallback"
    }
    
    return intent_to_node.get(state.intent, "fallback")


def should_respond(state: AgentState) -> Literal["response", "fallback"]:
    """Determine if we should go to response or fallback"""
    if state.error or state.needs_clarification:
        return "fallback"
    return "response"


def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph agent graph.
    
    Graph structure:
    
    START -> classify_intent -> [route_by_intent]
                                    |
            +------ validation -----+
            |                       |
            +--- force_validate ----+
            |                       |
            +--- delete_document ---+
            |                       |
            +--- export_invoices ---+
            |                       |
            +------ rag_query ------+
            |                       |
            +--- list_documents ----+--> [should_respond] --> response --> END
            |                       |              |
            +------ get_details ----+              +----> fallback -+
            |                       |                               |
            +---- general_chat -----+                               |
            |                                                       |
            +--------------- fallback <-----------------------------+
    """
    
    # Create the graph with AgentState
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("validation", validation_node)
    graph.add_node("force_validate", force_validate_node)
    graph.add_node("delete_document", delete_document_node)
    graph.add_node("export_invoices", export_invoices_node)
    graph.add_node("rag_query", rag_query_node)
    graph.add_node("list_documents", list_documents_node)
    graph.add_node("get_details", get_details_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("response", response_node)
    
    # Set entry point
    graph.set_entry_point("classify_intent")
    
    # Add conditional edges from intent classification
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "validation": "validation",
            "force_validate": "force_validate",
            "delete_document": "delete_document",
            "export_invoices": "export_invoices",
            "rag_query": "rag_query",
            "list_documents": "list_documents",
            "get_details": "get_details",
            "general_chat": "general_chat",
            "fallback": "fallback"
        }
    )
    
    # Add edges from tool nodes to response check
    for node in ["validation", "force_validate", "delete_document", "export_invoices", "rag_query", "list_documents", "get_details", "general_chat"]:
        graph.add_conditional_edges(
            node,
            should_respond,
            {
                "response": "response",
                "fallback": "fallback"
            }
        )
    
    # Fallback always goes to response
    graph.add_edge("fallback", "response")
    
    # Response is the end
    graph.add_edge("response", END)
    
    return graph


# Compile the graph
_compiled_graph = None


def get_agent_graph():
    """Get the compiled agent graph"""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_agent_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph


async def run_agent(
    message: str,
    session_id: str,
    document_id: str | None = None
) -> AgentState:
    """
    Run the agent with a user message.
    
    Args:
        message: The user's message
        session_id: Chat session ID
        document_id: Optional document ID for document-specific queries
    
    Returns:
        Final agent state with response
    """
    import traceback
    
    try:
        graph = get_agent_graph()
        
        initial_state = AgentState(
            user_message=message,
            session_id=session_id,
            document_id=document_id
        )
        
        logger.info(f"Running agent for session {session_id}")
        
        # Run the graph
        final_state = await graph.ainvoke(initial_state)
        
        # Convert dict back to AgentState if needed
        if isinstance(final_state, dict):
            final_state = AgentState(**final_state)
        
        logger.info(f"Agent completed - Intent: {final_state.intent}, Tool: {final_state.tool_name}")
        
        return final_state
    except Exception as e:
        logger.error(f"AGENT ERROR: {type(e).__name__}: {str(e)}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise
