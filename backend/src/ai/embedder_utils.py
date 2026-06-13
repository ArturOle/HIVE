"""Utility for automatic embedder provider fallback."""

from __future__ import annotations

from typing import Any
from src.ai.providers import QwenEmbedderClient, QwenProviderConfig


def get_embedder_safe(
    primary_embedder: Any | None = None,
    fallback_to_qwen: bool = True,
) -> Any:
    """Get embedder with automatic fallback to Qwen3 if primary is unavailable.
    
    Args:
        primary_embedder: The primary embedder to use (e.g., OpenAI, Gemini)
        fallback_to_qwen: If True and primary is None, use Qwen3 fallback
    
    Returns:
        The primary embedder if available, otherwise Qwen3 embedder, or None.
        
    Example:
        >>> from src.ai.providers import OpenAIEmbedderClient, OpenAIProviderConfig
        >>> embedder = get_embedder_safe(None, fallback_to_qwen=True)
        >>> # Returns QwenEmbedderClient if OpenAI not configured
    """
    
    # If we have a primary embedder, use it
    if primary_embedder is not None:
        return primary_embedder
    
    # If fallback is disabled, return None
    if not fallback_to_qwen:
        return None
    
    # Try to use Qwen3 as fallback
    try:
        print("Primary embedder not available. Using Qwen3-Embedding-0.6B fallback...")
        config = QwenProviderConfig()
        embedder = QwenEmbedderClient(config)
        return embedder
    except Exception as e:
        print(f"⚠️  Failed to initialize Qwen3 fallback embedder: {e}")
        print("   Make sure to install transformers: pip install transformers torch")
        print(f"   And download the model to: {config.get_model_path()}")
        return None
