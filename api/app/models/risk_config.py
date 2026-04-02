"""Risk configuration model — stores configurable risk tier thresholds."""

from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RiskConfig(Base, UUIDMixin, TimestampMixin):
    """Configurable risk tier thresholds.

    Stores the active score-to-tier mapping so thresholds can be changed
    on-the-fly from the admin portal without code changes or re-deployment.

    score_mode:
        "inverted" — lower score = higher risk (MedBed device default)
        "normal"   — higher score = higher risk (traditional)

    tier_thresholds:
        JSON dict mapping tier name → [lower_bound, upper_bound).
        Example for inverted mode:
        {
            "critical": [0.0, 0.1],
            "high":     [0.1, 0.2],
            "moderate": [0.2, 0.4],
            "low":      [0.4, 1.01]
        }
    """

    __tablename__ = "risk_configs"

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    score_mode: Mapped[str] = mapped_column(String(20), default="inverted")
    tier_thresholds: Mapped[dict] = mapped_column(JSON, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Default")


# Default thresholds for MedBed inverted scores
DEFAULT_TIER_THRESHOLDS = {
    "critical": [0.0, 0.1],
    "high": [0.1, 0.2],
    "moderate": [0.2, 0.4],
    "low": [0.4, 1.01],
}
