"""Streamlit frontend for H.I.V.E. Mind multi-message chat interface."""

import asyncio
import json
import os
from typing import Any

import httpx
import streamlit as st

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 600.0


async def query_backend(query: str, top_k: int | None = None) -> dict[str, Any]:
    """Query the backend orchestrator via HTTP."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        payload = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        
        response = await client.post(
            f"{BACKEND_URL}/read",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def format_backend_response(response: dict[str, Any]) -> str:
    """Format the backend response for display."""
    data = response.get("data", {})
    
    # Extract the response content
    if "response" in data:
        resp_obj = data["response"]
        if isinstance(resp_obj, dict):
            # Format structured response
            result_lines = []
            if "summary" in resp_obj:
                result_lines.append(f"**Summary:** {resp_obj['summary']}")
            if "details" in resp_obj:
                result_lines.append(f"**Details:** {resp_obj['details']}")
            if "results" in resp_obj:
                result_lines.append("**Results:**")
                for item in resp_obj["results"]:
                    result_lines.append(f"  - {json.dumps(item, indent=2)}")
            return "\n\n".join(result_lines) if result_lines else json.dumps(resp_obj, indent=2)
        else:
            return str(resp_obj)
    
    # Fallback: format raw data
    if data:
        return json.dumps(data, indent=2)
    
    return "No response from backend"


def main() -> None:
    """Main Streamlit application."""
    st.set_page_config(
        page_title="H.I.V.E. Mind",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.title("🧠 H.I.V.E. Mind Interface")
    st.markdown("*Multi-message conversational interface with knowledge base retrieval*")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        backend_url = st.text_input(
            "Backend URL",
            value=BACKEND_URL,
            help="URL of the backend orchestrator API",
        )
        top_k = st.slider(
            "Top-K Results",
            min_value=1,
            max_value=50,
            value=5,
            help="Number of top results to retrieve",
        )
        st.markdown("---")
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                st.markdown(message["content"])
    
    # Accept user input and process
    if user_input := st.chat_input("Ask H.I.V.E. about your problem..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Query backend and get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Use asyncio to run the async backend call
                    response = asyncio.run(
                        query_backend(query=user_input, top_k=top_k)
                    )
                    
                    # Format and display response
                    formatted_response = format_backend_response(response)
                    st.markdown(formatted_response)
                    
                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": formatted_response,
                    })
                    
                except httpx.ConnectError as e:
                    error_msg = f"❌ Cannot connect to backend at {backend_url}. Please ensure it's running."
                    st.error(error_msg)
                    logger_msg = f"Connection error: {e}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })
                except httpx.TimeoutException:
                    error_msg = "❌ Backend request timed out. Please try again or check backend performance."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })
                except httpx.HTTPError as e:
                    error_msg = f"❌ Backend error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })


if __name__ == "__main__":
    main()