"""ML model serving configuration."""

import os

import torch


class ModelConfig:
    """Configuration for the BioClinical ModernBERT model."""

    MODEL_NAME: str = os.getenv(
        "MODEL_NAME", "thomas-sounack/BioClinical-ModernBERT-base"
    )
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    TORCH_DTYPE = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    MAX_LENGTH_ENTRY: int = 512
    MAX_LENGTH_REPORT: int = 8192
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "16"))

    @classmethod
    def info(cls) -> dict:
        return {
            "model_name": cls.MODEL_NAME,
            "device": cls.DEVICE,
            "dtype": str(cls.TORCH_DTYPE),
            "max_length_entry": cls.MAX_LENGTH_ENTRY,
            "max_length_report": cls.MAX_LENGTH_REPORT,
            "cuda_available": torch.cuda.is_available(),
        }
