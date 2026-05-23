"""Provider module with local Qwen3 embedding model support."""

from __future__ import annotations

import torch
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.ai.providers.abstract_provider import (
    AbstractProviderEmbedderClient,
)


class QwenProviderConfig(BaseSettings):
    """Configuration for Qwen3 Embedding provider."""

    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        validation_alias="QWEN_MODEL_NAME"
    )
    
    model_cache_dir: str = Field(
        default="./models/qwen",
        validation_alias="QWEN_MODEL_CACHE_DIR"
    )
    
    device: str = Field(
        default_factory=lambda: "cuda" if torch.cuda.is_available() else "cpu",
        validation_alias="QWEN_DEVICE"
    )
    
    max_seq_length: int = Field(
        default=8192,
        validation_alias="QWEN_MAX_SEQ_LENGTH"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )

    def get_model_path(self) -> Path:
        """Get the full model path."""
        model_path = Path(self.model_cache_dir).expanduser().absolute()
        model_path.mkdir(parents=True, exist_ok=True)
        return model_path


class QwenEmbedderClient(AbstractProviderEmbedderClient):
    """Local embedding adapter for Qwen3 Embedding model."""

    def __init__(self, config: QwenProviderConfig | None = None):
        """Initialize Qwen3 embedder with local model.
        
        Args:
            config: QwenProviderConfig instance. If None, creates default config
                   from environment variables or defaults.
        
        Raises:
            RuntimeError: If required dependencies are missing.
        """
        if config is None:
            config = QwenProviderConfig()
        
        self.config = config
        self._client = None
        self._model = None
        self._tokenizer = None
    
    def _load_model(self) -> None:
        """Lazy-load the model and tokenizer on first use."""
        if self._model is not None:
            return
        
        try:
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "transformers library is required for Qwen3 embeddings. "
                "Install with: pip install transformers torch"
            ) from exc
        
        model_path = self.config.get_model_path()
        model_name = self.config.model_name
        
        print(f"Loading Qwen3 Embedding model from: {model_path}")
        print(f"Model: {model_name}")
        print(f"Device: {self.config.device}")
        
        try:
            # Try to load from local cache first
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(model_path),
                trust_remote_code=True,
            )
            self._model = AutoModel.from_pretrained(
                model_name,
                cache_dir=str(model_path),
                trust_remote_code=True,
            ).to(self.config.device)
            
            print(f"✓ Model loaded successfully on {self.config.device}")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Qwen3 model. Make sure the model is downloaded to "
                f"{model_path} or that you have internet access to download it. "
                f"Error: {exc}"
            ) from exc

    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using Qwen3 model.
        
        Args:
            text: Input text to embed.
            
        Returns:
            List of embedding floats.
        """
        import asyncio
        
        # Lazy-load model on first use
        if self._model is None:
            self._load_model()
        
        # Run embedding in thread pool to avoid blocking
        embedding = await asyncio.to_thread(self._embed_sync, text)
        return embedding
    
    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous embedding (runs in thread pool)."""
        import torch
        
        if not text.strip():
            # Return zero vector for empty text
            return [0.0] * 768  # Qwen3 default embedding dimension
        
        # Tokenize input
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_seq_length,
        ).to(self.config.device)
        
        # Get embeddings
        with torch.no_grad():
            outputs = self._model(**inputs)
            # Use mean pooling over the sequence dimension
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        # Convert to list of floats
        embedding_list = embeddings[0].cpu().tolist()
        
        return embedding_list

