"""Admin router — manage risk configuration and platform settings."""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.base import get_db
from app.models.risk_config import DEFAULT_TIER_THRESHOLDS, RiskConfig
from app.utils.auth import get_current_user
from app.utils.risk_tiers import invalidate_risk_config_cache

logger = logging.getLogger(__name__)

router = APIRouter()


class RiskConfigOut(BaseModel):
    """Risk configuration response."""

    id: str
    score_mode: str
    tier_thresholds: dict
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class RiskConfigUpdate(BaseModel):
    """Risk configuration update request."""

    score_mode: str | None = None
    tier_thresholds: dict | None = None
    name: str | None = None


@router.get("/risk-config", response_model=RiskConfigOut)
async def get_risk_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get the active risk configuration."""
    result = await db.execute(
        select(RiskConfig).where(RiskConfig.is_active.is_(True)).limit(1)
    )
    config = result.scalar_one_or_none()

    if not config:
        # Create default config on first access
        config = RiskConfig(
            score_mode="inverted",
            tier_thresholds=DEFAULT_TIER_THRESHOLDS,
            name="Default",
            is_active=True,
        )
        db.add(config)
        await db.flush()

    return RiskConfigOut(
        id=str(config.id),
        score_mode=config.score_mode,
        tier_thresholds=config.tier_thresholds,
        name=config.name,
        is_active=config.is_active,
    )


@router.put("/risk-config", response_model=RiskConfigOut)
async def update_risk_config(
    update: RiskConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update the active risk configuration.

    Changes take effect immediately for all new API responses.
    Existing stored risk_tier values on entries are not retroactively updated
    but tiers are recomputed at read time.
    """
    result = await db.execute(
        select(RiskConfig).where(RiskConfig.is_active.is_(True)).limit(1)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = RiskConfig(
            score_mode="inverted",
            tier_thresholds=DEFAULT_TIER_THRESHOLDS,
            name="Default",
            is_active=True,
        )
        db.add(config)

    # Validate tier_thresholds if provided
    if update.tier_thresholds is not None:
        required_tiers = {"critical", "high", "moderate", "low"}
        provided_tiers = set(update.tier_thresholds.keys())
        if not required_tiers.issubset(provided_tiers):
            missing = required_tiers - provided_tiers
            raise HTTPException(
                status_code=422,
                detail=f"Missing required tiers: {missing}",
            )
        for tier_name, bounds in update.tier_thresholds.items():
            if (
                not isinstance(bounds, list)
                or len(bounds) != 2
                or not all(isinstance(b, (int, float)) for b in bounds)
            ):
                raise HTTPException(
                    status_code=422,
                    detail=f"Tier '{tier_name}' must be [lower_bound, upper_bound]",
                )
        config.tier_thresholds = update.tier_thresholds

    if update.score_mode is not None:
        if update.score_mode not in ("inverted", "normal"):
            raise HTTPException(
                status_code=422,
                detail="score_mode must be 'inverted' or 'normal'",
            )
        config.score_mode = update.score_mode

    if update.name is not None:
        config.name = update.name

    await db.flush()

    # Invalidate the in-memory cache so all processes pick up changes
    invalidate_risk_config_cache()

    logger.info(
        "Risk config updated: mode=%s, thresholds=%s",
        config.score_mode,
        config.tier_thresholds,
    )

    return RiskConfigOut(
        id=str(config.id),
        score_mode=config.score_mode,
        tier_thresholds=config.tier_thresholds,
        name=config.name,
        is_active=config.is_active,
    )


# ---------------------------------------------------------------------------
# UMLS cache management
# ---------------------------------------------------------------------------


def _get_cache_redis_url() -> str:
    """Build the Redis URL for the UMLS cache DB."""
    settings = get_settings()
    parts = settings.REDIS_URL.rsplit("/", 1)
    return f"{parts[0]}/{settings.REDIS_CACHE_DB}"


class CacheStatsOut(BaseModel):
    """UMLS cache statistics response."""

    condition_keys: int
    anatomy_keys: int
    total_keys: int


@router.get("/cache/umls", response_model=CacheStatsOut)
async def get_umls_cache_stats(
    _user=Depends(get_current_user),
):
    """Get UMLS cache statistics (key counts by type)."""
    r = aioredis.from_url(
        _get_cache_redis_url(), decode_responses=True, socket_connect_timeout=2
    )
    try:
        condition_keys = []
        async for key in r.scan_iter("umls:condition:*", count=1000):
            condition_keys.append(key)

        anatomy_keys = []
        async for key in r.scan_iter("umls:anatomy:*", count=1000):
            anatomy_keys.append(key)

        return CacheStatsOut(
            condition_keys=len(condition_keys),
            anatomy_keys=len(anatomy_keys),
            total_keys=len(condition_keys) + len(anatomy_keys),
        )
    finally:
        await r.aclose()


class CacheFlushOut(BaseModel):
    """UMLS cache flush response."""

    deleted: int
    message: str


@router.post("/cache/umls/flush", response_model=CacheFlushOut)
async def flush_umls_cache(
    _user=Depends(get_current_user),
):
    """Flush all cached UMLS lookups from Redis.

    This forces the next analysis pipeline run to re-query the UMLS API
    for all conditions and anatomy locations.
    """
    r = aioredis.from_url(
        _get_cache_redis_url(), decode_responses=True, socket_connect_timeout=2
    )
    try:
        keys = []
        async for key in r.scan_iter("umls:*", count=1000):
            keys.append(key)

        deleted = 0
        if keys:
            deleted = await r.delete(*keys)

        logger.info("UMLS cache flushed: %d keys deleted", deleted)
        return CacheFlushOut(
            deleted=deleted,
            message=f"Flushed {deleted} cached UMLS lookups",
        )
    finally:
        await r.aclose()
