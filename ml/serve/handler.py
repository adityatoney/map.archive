"""FastAPI ML inference service for BioClinical ModernBERT.

Provides embedding generation via HTTP. Model loads lazily on first request
to avoid blocking Docker Compose health checks during startup.
"""

import logging
import time

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from serve.config import ModelConfig
except ImportError:
    from config import ModelConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MedBed ML Service",
    description="BioClinical ModernBERT embedding service",
    version="0.1.0",
)

# Global model state — lazy loaded
_tokenizer = None
_model = None
_model_loaded = False
_load_time = None


class EmbedRequest(BaseModel):
    texts: list[str]
    max_length: int = 512


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimension: int
    count: int


def _load_model():
    """Load the model on first use (lazy loading)."""
    global _tokenizer, _model, _model_loaded, _load_time

    if _model_loaded:
        return

    logger.info("Loading model: %s (device: %s)", ModelConfig.MODEL_NAME, ModelConfig.DEVICE)
    start = time.time()

    try:
        from transformers import AutoModel, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(ModelConfig.MODEL_NAME)
        _model = AutoModel.from_pretrained(
            ModelConfig.MODEL_NAME,
            torch_dtype=ModelConfig.TORCH_DTYPE,
        )
        _model.to(ModelConfig.DEVICE)
        _model.eval()

        _load_time = time.time() - start
        _model_loaded = True
        logger.info("Model loaded in %.1f seconds", _load_time)
    except Exception as e:
        logger.error("Failed to load model: %s", e)
        raise


@app.get("/health")
async def health():
    """Health check — reports model loaded status."""
    return {
        "status": "ok",
        "model_loaded": _model_loaded,
        "model_name": ModelConfig.MODEL_NAME,
        "device": ModelConfig.DEVICE,
        "load_time_seconds": _load_time,
    }


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """Generate embeddings for a batch of texts.

    Uses CLS token pooling from the last hidden state.
    """
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    # Lazy load model on first request
    if not _model_loaded:
        try:
            _load_model()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Model failed to load: {str(e)}",
            )

    try:
        embeddings = _generate_embeddings(request.texts, request.max_length)
        return EmbedResponse(
            embeddings=embeddings,
            model=ModelConfig.MODEL_NAME,
            dimension=len(embeddings[0]) if embeddings else 0,
            count=len(embeddings),
        )
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _generate_embeddings(texts: list[str], max_length: int = 512) -> list[list[float]]:
    """Generate embeddings using CLS token pooling.

    Processes in batches for memory efficiency.
    """
    all_embeddings = []
    total_batches = (len(texts) + ModelConfig.BATCH_SIZE - 1) // ModelConfig.BATCH_SIZE
    start_time = time.time()

    for batch_num, i in enumerate(range(0, len(texts), ModelConfig.BATCH_SIZE), 1):
        batch = texts[i : i + ModelConfig.BATCH_SIZE]
        logger.info("Embedding batch %d/%d (%d texts)", batch_num, total_batches, len(batch))

        inputs = _tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        inputs = {k: v.to(ModelConfig.DEVICE) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = _model(**inputs)

        # CLS token pooling (first token)
        cls_embeddings = outputs.last_hidden_state[:, 0, :]

        # Normalize
        norms = torch.norm(cls_embeddings, dim=1, keepdim=True)
        cls_embeddings = cls_embeddings / norms.clamp(min=1e-8)

        all_embeddings.extend(cls_embeddings.cpu().float().numpy().tolist())

    elapsed = time.time() - start_time
    logger.info("Embedded %d texts in %.1f seconds (%.1f texts/sec)", len(texts), elapsed, len(texts) / max(elapsed, 0.001))

    return all_embeddings
