"""Provider module with local Qwen3 embedding and LLM model support."""

from __future__ import annotations

import torch
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langfuse import observe

from ai.providers.abstract_provider import (
    AbstractProviderEmbedderClient,
    AbstractProviderLLMClient,
)


class QwenProviderConfig(BaseSettings):
    """Configuration for Qwen3 Embedding and LLM provider."""

    llm_model: str = Field(
        default="Qwen/Qwen3-2B",
        validation_alias="QWEN_LLM_MODEL"
    )

    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        validation_alias="QWEN_MODEL_NAME"
    )
    
    model_cache_dir: str = Field(
        default="./models/qwen",
        validation_alias="QWEN_MODEL_CACHE_DIR"
    )
    
    device: str = Field(
        default="cuda",
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
            config: QwenProviderConfig instance. If None, creates default config.
        
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
        """Lazy-load the embedding model and tokenizer on first use."""
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
            
            print(f"✓ Embedding model loaded successfully on {self.config.device}")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Qwen3 model. Make sure the model is downloaded to "
                f"{model_path} or that you have internet access to download it. "
                f"Error: {exc}"
            ) from exc

    @observe(as_type="generation")
    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using Qwen3 model.
        
        Args:
            text: Input text to embed.
            
        Returns:
            List of embedding floats.
        """
        import asyncio
        
        if self._model is None:
            self._load_model()
        
        embedding = await asyncio.to_thread(self._embed_sync, text)
        return embedding
    
    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous embedding (runs in thread pool)."""
        import torch
        
        if not text.strip():
            return [0.0] * 768  # Qwen3 default embedding dimension
        
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_seq_length,
        ).to(self.config.device)
        
        with torch.no_grad():
            outputs = self._model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        return embeddings[0].cpu().tolist()


class QwenLLMClient(AbstractProviderLLMClient):
    """Local text generation adapter for Qwen3 LLM models."""

    def __init__(self, config: QwenProviderConfig | None = None):
        """Initialize Qwen3 LLM with local model.

        Args:
            config: QwenProviderConfig instance. If None, creates default config.
        """
        if config is None:
            config = QwenProviderConfig()
            
        self.config = config
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        """Lazy-load the generation model and tokenizer on first use."""
        if self._model is not None:
            return

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "transformers library is required for Qwen3 generation. "
                "Install with: pip install transformers torch"
            ) from exc

        model_path = self.config.get_model_path()
        llm_model = self.config.llm_model

        print(f"Loading Qwen3 LLM from: {model_path}")
        print(f"Model: {llm_model}")
        print(f"Device: {self.config.device}")

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                llm_model,
                cache_dir=str(model_path),
                trust_remote_code=True,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                llm_model,
                cache_dir=str(model_path),
                trust_remote_code=True,
                torch_dtype="auto",  # Automatically uses float16/bfloat16 if supported
            ).to(self.config.device)

            print(f"✓ LLM model loaded successfully on {self.config.device}")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Qwen3 LLM model. Make sure the model is downloaded to "
                f"{model_path} or that you have internet access. Error: {exc}"
            ) from exc

    @observe(as_type="generation")
    async def ainvoke(self, prompt: str) -> str:
        """Asynchronously invoke the Qwen3 LLM.

        Args:
            prompt: Text prompt to feed the model.

        Returns:
            Generated text response.
        """
        import asyncio

        if self._model is None:
            self._load_model()

        # Run text generation in a separate thread pool to prevent blocking the event loop
        response = await asyncio.to_thread(self._invoke_sync, prompt)
        return response

    def _invoke_sync(self, prompt: str) -> str:
        """Synchronous generation execution loop."""
        import torch

        if not prompt.strip():
            return ""

        # Format using template if model is a chat variant, otherwise fall back to pure text
        if hasattr(self._tokenizer, "apply_chat_template") and self._tokenizer.chat_template:
            messages = [{"role": "user", "content": prompt}]
            text = self._tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
        else:
            text = prompt

        model_inputs = self._tokenizer([text], return_tensors="pt").to(self.config.device)

        with torch.no_grad():
            generated_ids = self._model.generate(
                **model_inputs,
                max_new_tokens=512,  # Adjust default headroom as necessary
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id
            )
        
        # Strip out the input tokens from the returned payload
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response