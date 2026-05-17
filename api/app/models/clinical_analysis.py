"""Clinical analysis model — LLM-powered diagnostic reasoning."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ClinicalAnalysis(Base, UUIDMixin, TimestampMixin):
    """LLM-generated clinical analysis for a scan session.

    Separate from RecoveryPlan: recovery plan = structured treatment data;
    clinical analysis = deep diagnostic reasoning (cascade chains, root systems).
    """

    __tablename__ = "clinical_analyses"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False, unique=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # LLM-generated content
    systemic_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_systems: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cascade_chains: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_patterns: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actionable_insights: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metadata
    analysis_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="template"
    )  # "llm" or "template"
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Always present
    disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "IMPORTANT DISCLAIMER: Medical Analytics Platform is an analytical exploration tool, "
            "not a medical diagnostic device. The information presented here is derived "
            "from frequency-based scan data analysis and pattern recognition algorithms. "
            "It does NOT constitute medical advice, diagnosis, or treatment recommendations. "
            "Always consult a qualified healthcare professional before making any health "
            "decisions. The patterns and correlations identified are for informational "
            "and exploratory purposes only."
        ),
    )

    # Relationships
    session = relationship("ScanSession", back_populates="clinical_analysis")
    patient = relationship("Patient", back_populates="clinical_analyses")
