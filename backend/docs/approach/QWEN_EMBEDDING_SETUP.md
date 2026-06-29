# Qwen3 Embedding Model - Setup Guide

## Overview
Qwen3-Embedding-0.6B is a lightweight local embedding model that serves as a fallback when cloud-based embedders (OpenAI, Gemini) are unavailable or not configured.

## Model Information
- **Model**: Qwen/Qwen3-Embedding-0.6B
- **Size**: ~600MB
- **Dimensions**: 768
- **Local Execution**: CPU/GPU (no API calls needed)
- **License**: Qwen License (check [model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B))

## Where to Place the Model

### Option 1: Automatic Download (Recommended)
If you have internet access and Hugging Face configured, the model will **automatically download** on first use to:

```
./models/qwen/
```

Or set a custom location via environment variable:
```bash
export QWEN_MODEL_CACHE_DIR="~/my_models/qwen"
```

### Option 2: Manual Download
If you want to pre-download the model (useful for offline environments):

#### Step 1: Install Dependencies
```bash
pip install transformers torch huggingface-hub
```

#### Step 2: Download Model
Using Python:
```python
from huggingface_hub import snapshot_download
import os

cache_dir = "./models/qwen"  # Or your preferred path
model_id = "Qwen/Qwen3-Embedding-0.6B"

snapshot_download(repo_id=model_id, cache_dir=cache_dir)
print(f"✓ Model downloaded to: {cache_dir}")
```

Or using HF CLI:
```bash
huggingface-cli download Qwen/Qwen3-Embedding-0.6B --cache-dir ./models/qwen
```

#### Step 3: Verify Installation
```bash
ls -la ./models/qwen/
# Should show model files like: config.json, pytorch_model.bin, etc.
```

## Configuration

### Via Environment Variables (.env)
```env
# Qwen model configuration
QWEN_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
QWEN_MODEL_CACHE_DIR=./models/qwen
QWEN_DEVICE=cpu
QWEN_MAX_SEQ_LENGTH=8192
```

### Device Options
- `cpu`: CPU inference (slower, no GPU required)
- `cuda`: NVIDIA GPU (requires CUDA-capable GPU and `torch[cuda]`)
- `mps`: Apple Metal Performance Shaders (macOS only)

For GPU:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## Usage

### Basic Usage with Fallback
```python
from src.ai.embedder_utils import get_embedder_safe
from src.logic.orchestrator import AgentOrchestrator

# embedder will automatically use Qwen3 if no primary embedder provided
embedder = get_embedder_safe(primary_embedder=None, fallback_to_qwen=True)

orchestrator = AgentOrchestrator(embedder=embedder)
await orchestrator.initialize()
```

### Direct Qwen3 Usage
```python
from src.ai.providers import QwenEmbedderClient, QwenProviderConfig

# With defaults (models downloaded to ./models/qwen/)
config = QwenProviderConfig()
embedder = QwenEmbedderClient(config)

# Generate embeddings
embedding = await embedder.embed("What is machine learning?")
print(f"Embedding dimension: {len(embedding)}")  # 768
```

### Custom Configuration
```python
from src.ai.providers import QwenEmbedderClient, QwenProviderConfig
from pathlib import Path

config = QwenProviderConfig(
    model_name="Qwen/Qwen3-Embedding-0.6B",
    model_cache_dir="/mnt/models/qwen",  # Custom path
    device="cuda",  # Use GPU
    max_seq_length=8192
)
embedder = QwenEmbedderClient(config)
```

## Troubleshooting

### Model Not Found
```
RuntimeError: Failed to load Qwen3 model. Make sure the model is downloaded to ./models/qwen/
```

**Solution**: Download the model manually using the steps above.

### Out of Memory (OOM)
Qwen3-Embedding-0.6B is lightweight, but if you hit memory issues:
```python
# Use CPU instead of GPU
config = QwenProviderConfig(device="cpu")

# Or reduce batch size in your inference code
```

### "transformers" Not Found
```
ImportError: transformers library is required...
```

**Solution**:
```bash
pip install transformers torch
```

### Slow First Inference
First embedding generation is slow because the model loads into memory. This is normal and only happens once per session.

## Performance

### Benchmarks (on CPU)
- First embedding load: ~2-5 seconds (model initialization)
- Subsequent embeddings: ~100-200ms per 512 tokens

### Memory
- Model RAM: ~1.2 GB
- Per-inference: ~100-300 MB

For production: consider GPU for <50ms latency.

## Integration with HIVE

### In Orchestrator
```python
from src.logic.orchestrator import AgentOrchestrator
from src.ai.embedder_utils import get_embedder_safe

# Automatically falls back to Qwen3
embedder = get_embedder_safe(primary_embedder=None)

orchestrator = AgentOrchestrator(embedder=embedder)
await orchestrator.initialize()

# Use normally
result = await orchestrator.run(mode="read", text="Your query here")
```

### In Notebooks
Update your provider selection in `knowledge_base_test.ipynb`:

```python
from src.ai.embedder_utils import get_embedder_safe

# Instead of:
# embedder = OpenAIEmbedderClient(cfg)

# Use:
embedder = get_embedder_safe(primary_embedder=None, fallback_to_qwen=True)
```

## Directory Structure After Setup
```
HIVE/
├── models/
│   └── qwen/
│       ├── config.json
│       ├── pytorch_model.bin
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       └── ...
├── src/
│   └── ai/
│       ├── providers/
│       │   ├── qwen.py          # ← New Qwen provider
│       │   └── ...
│       └── embedder_utils.py    # ← New utility for fallback
└── .env
```

## Related Documentation
- [Neo4j Embedding Integration](../database/NEO4J_APPROACH.md)
- [Provider Architecture](./INFERENCE_KNOWLEDGE_ACQUISITION.md)
- [Memory Model](./MEMORY_MODEL.md)
