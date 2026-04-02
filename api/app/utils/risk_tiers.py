"""Central risk tier computation utility.

Single source of truth for converting raw scores to tier labels.
All tier computation in the codebase should route through this module.

Supports configurable thresholds stored in the RiskConfig database table,
with an in-memory cache (TTL-based) to avoid per-request DB hits.
"""

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: dict[str, Any] = {"config": None, "expires": 0.0}
CACHE_TTL = 60  # seconds


async def get_active_risk_config(db: AsyncSession):
    """Fetch the active RiskConfig from DB, with in-memory caching.

    Returns None if no config exists (will use hardcoded defaults).
    """
    from app.models.risk_config import RiskConfig

    now = time.time()
    if _cache["config"] is not None and now < _cache["expires"]:
        return _cache["config"]

    result = await db.execute(
        select(RiskConfig).where(RiskConfig.is_active.is_(True)).limit(1)
    )
    config = result.scalar_one_or_none()
    if config:
        _cache["config"] = config
        _cache["expires"] = now + CACHE_TTL
    return config


def invalidate_risk_config_cache():
    """Call after admin updates thresholds to force re-read from DB."""
    _cache["config"] = None
    _cache["expires"] = 0.0


def score_to_tier(score: float, config=None) -> str:
    """Map a raw 0-1 score to a risk tier using the active config.

    If config is None, uses hardcoded inverted defaults (MedBed device).
    """
    if config is None:
        return _score_to_tier_inverted_default(score)

    thresholds = config.tier_thresholds
    for tier_name in ["critical", "high", "moderate", "low"]:
        bounds = thresholds.get(tier_name, [0, 1.01])
        low_bound, high_bound = bounds[0], bounds[1]
        if low_bound <= score < high_bound:
            return tier_name

    # Fallback for edge cases (score exactly at boundary)
    return "low"


def _score_to_tier_inverted_default(score: float) -> str:
    """Hardcoded fallback for inverted scores (lower = worse).

    Matches MedBed device interpretation:
      0.0 - 0.1: critical
      0.1 - 0.2: high
      0.2 - 0.4: moderate
      0.4+:      low
    """
    if score < 0.1:
        return "critical"
    elif score < 0.2:
        return "high"
    elif score < 0.4:
        return "moderate"
    return "low"


def is_score_inverted(config=None) -> bool:
    """Return True if lower scores mean higher risk."""
    if config is None:
        return True  # MedBed default
    return config.score_mode == "inverted"


def score_to_severity(score: float, config=None) -> float:
    """Convert a raw score to a 0-1 severity value (higher = more severe).

    For inverted mode: low raw score = high severity, so severity = 1 - score.
    For normal mode: high raw score = high severity, so severity = score.
    """
    if is_score_inverted(config):
        return 1.0 - score
    return score


def score_to_wellness(score: float, config=None) -> float:
    """Convert a raw score to a 0-1 wellness value (higher = healthier).

    For inverted mode: high raw score = healthy, so wellness = score.
    For normal mode: low raw score = healthy, so wellness = 1 - score.
    """
    if is_score_inverted(config):
        return score
    return 1.0 - score
