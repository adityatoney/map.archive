"""Condition trend model for temporal analysis."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ConditionTrend(Base, UUIDMixin, TimestampMixin):
    """Tracks how a condition's score changes across multiple scan sessions."""

    __tablename__ = "condition_trends"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )

    # Condition identification
    condition_icd10: Mapped[str | None] = mapped_column(String(20), nullable=True)
    condition_name: Mapped[str] = mapped_column(Text, nullable=False)
    organ_system: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Trend metrics
    trend_direction: Mapped[str] = mapped_column(
        String(20), nullable=False, default="stable"
    )  # improving, worsening, stable, volatile
    trend_slope: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sessions_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_score: Mapped[float] = mapped_column(Float, nullable=False)
    last_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Change point details: list of {session_id, date, old_score, new_score}
    change_points: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="trends")
