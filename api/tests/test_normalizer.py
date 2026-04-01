"""Normalizer service tests (mock mode)."""

import pytest
from app.services.normalizer import NormalizerService


@pytest.mark.asyncio
async def test_mock_normalize_known_condition():
    """Known conditions should return mapped ICD-10 codes."""
    service = NormalizerService()
    result = await service.normalize_condition("ANAEMIA")
    assert result["icd10"] == "D64.9"
    assert result["snomed"] == "271737000"


@pytest.mark.asyncio
async def test_mock_normalize_unknown_condition():
    """Unknown conditions should return a deterministic placeholder code."""
    service = NormalizerService()
    result = await service.normalize_condition("UNKNOWN CONDITION XYZ")
    assert result["icd10"] is not None
    assert result["icd10"].startswith("U")
    # Should be deterministic
    result2 = await service.normalize_condition("UNKNOWN CONDITION XYZ")
    assert result["icd10"] == result2["icd10"]


@pytest.mark.asyncio
async def test_mock_normalize_anatomy():
    """Known anatomical locations should return FMA IDs."""
    service = NormalizerService()
    result = await service.normalize_anatomy("BODY OF MAN")
    assert result == "FMA:20394"


@pytest.mark.asyncio
async def test_mock_normalize_unknown_anatomy():
    """Unknown anatomical locations should return None."""
    service = NormalizerService()
    result = await service.normalize_anatomy("UNKNOWN LOCATION")
    assert result is None
