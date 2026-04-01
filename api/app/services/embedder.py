"""Embedding service — generates 768-dim vectors for condition entries.

Calls the ML service (BioClinical ModernBERT) via HTTP. Falls back to
deterministic mock embeddings when the ML service is unavailable.
"""

import hashlib
import logging

import httpx
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbedderService:
    """Generate embeddings for scan entry text."""

    def __init__(self):
        settings = get_settings()
        self.ml_service_url = settings.ML_SERVICE_URL
        self.embedding_dim = 768
        self._last_source: str = "mock"  # Track whether last call used real or mock

    @property
    def last_source(self) -> str:
        """Whether the last embed call used 'real' or 'mock' embeddings."""
        return self._last_source

    async def is_ml_service_available(self) -> bool:
        """Quick health check on the ML service."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ml_service_url}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("status") == "ok"
        except Exception:
            pass
        return False

    async def embed_entry(
        self, condition: str, anatomy: str | None = None, score: float = 0.0
    ) -> list[float]:
        """Generate a 768-dim embedding for a single report entry."""
        text = self._format_entry_text(condition, anatomy, score)
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Calls the ML service. Falls back to mock embeddings on failure.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Check if model is loaded; if not, warm it up first
                try:
                    health = await client.get(
                        f"{self.ml_service_url}/health", timeout=5.0
                    )
                    health_data = health.json()
                    if not health_data.get("model_loaded"):
                        logger.info(
                            "ML model not loaded yet, sending warm-up request "
                            "(this may take a few minutes on first run)..."
                        )
                        await client.post(
                            f"{self.ml_service_url}/embed",
                            json={"texts": ["warm-up"]},
                            timeout=300.0,  # 5 min for model download + load
                        )
                        logger.info("ML model warm-up complete.")
                except httpx.ConnectError:
                    raise  # ML service not running at all — go to mock fallback
                except Exception as e:
                    logger.warning("ML health/warm-up check failed: %s", e)

                # Send the real batch
                resp = await client.post(
                    f"{self.ml_service_url}/embed",
                    json={"texts": texts},
                    timeout=120.0,  # 2 min for large reports on CPU
                )
                resp.raise_for_status()
                data = resp.json()
                self._last_source = "real"
                logger.info(
                    "Got %d real embeddings from ML service (dim=%d)",
                    len(data["embeddings"]),
                    data.get("dimension", 0),
                )
                return data["embeddings"]
        except Exception as e:
            logger.warning(
                "ML service unavailable (%s), using mock embeddings for %d texts",
                str(e),
                len(texts),
            )
            self._last_source = "mock"
            return [self._mock_embedding(t) for t in texts]

    async def embed_full_report(self, entries: list[dict]) -> list[float]:
        """Embed an entire report as a single contextual unit."""
        report_text = " [SEP] ".join(
            self._format_entry_text(
                e.get("condition_name", ""),
                e.get("anatomical_location"),
                e.get("score", 0.0),
            )
            for e in entries
        )
        embeddings = await self.embed_texts([report_text])
        return embeddings[0]

    def _format_entry_text(
        self, condition: str, anatomy: str | None, score: float
    ) -> str:
        """Format an entry into text suitable for embedding."""
        parts = [condition]
        if anatomy:
            parts.append(f"located at {anatomy}")
        parts.append(f"deviation score {score:.3f}")
        return ", ".join(parts)

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding from text hash.

        Uses the text hash as a seed so the same input always produces
        the same vector. Vectors are unit-normalized.
        """
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(self.embedding_dim).astype(np.float32)
        # Unit normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
