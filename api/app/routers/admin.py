"""Admin router — manage risk configuration and platform settings."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
