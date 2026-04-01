"""Recovery plan model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

MEDICAL_DISCLAIMER = (
    "IMPORTANT DISCLAIMER: MedBed Insight is an analytical exploration tool, "
    "not a medical diagnostic device. The information presented here is derived "
    "from frequency-based scan data analysis and pattern recognition algorithms. "
    "It does NOT constitute medical advice, diagnosis, or treatment recommendations. "
    "Always consult a qualified healthcare professional before making any health "
    "decisions. The patterns and correlations identified are for informational "
    "and exploratory purposes only."
)


class RecoveryPlan(Base, UUIDMixin, TimestampMixin):
    """Generated recovery plan for a scan session."""

    __tablename__ = "recovery_plans"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False, unique=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Plan content
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    organ_system_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority_conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_interventions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lifestyle_recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    nutritional_recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    monitoring_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Always present
    disclaimer: Mapped[str] = mapped_column(
        Text, nullable=False, default=MEDICAL_DISCLAIMER
    )

    # Relationships
    session = relationship("ScanSession", back_populates="recovery_plan")
    patient = relationship("Patient", back_populates="recovery_plans")
