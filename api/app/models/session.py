"""Scan session model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.entry import ScanEntry
    from app.models.patient import Patient
    from app.models.recovery import RecoveryPlan


class ScanSession(Base, UUIDMixin, TimestampMixin):
    """A single scan session (one uploaded report)."""

    __tablename__ = "scan_sessions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    scan_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(
        String(20), default="pdf", nullable=False
    )  # pdf, csv, json, image

    # Top-level report metadata
    report_section: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "A) SIMULAR PROCESSES"
    organ_system: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Analysis status
    analysis_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed
    analysis_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Phase 2: Cluster analysis metadata (UMAP coords, summaries, labels)
    cluster_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Whether embeddings came from real ML service or mock fallback
    embedding_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="sessions")
    entries: Mapped[list["ScanEntry"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    recovery_plan: Mapped["RecoveryPlan | None"] = relationship(
        back_populates="session", uselist=False
    )
