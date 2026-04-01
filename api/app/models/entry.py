"""Scan entry model — one row per condition in a report."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ScanEntry(Base, UUIDMixin, TimestampMixin):
    """A single condition entry within a scan session."""

    __tablename__ = "scan_entries"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False, index=True
    )

    # Condition info
    condition_name: Mapped[str] = mapped_column(Text, nullable=False)
    condition_icd10: Mapped[str | None] = mapped_column(String(20), nullable=True)
    condition_snomed: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Anatomical location
    anatomical_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    anatomical_fma_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Organ system section from the report
    organ_system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_section: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # "A) SIMULAR PROCESSES" or "E) MICROORGANISMS"

    # Score and ratios
    score: Mapped[float] = mapped_column(Float, nullable=False)
    green_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    red_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Condition markers (e.g., "# D", "# G", "# R")
    marker: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ML-generated fields (populated after analysis pipeline)
    embedding_vector = mapped_column(Vector(768), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low, moderate, high, critical

    # Relationships
    session = relationship("ScanSession", back_populates="entries")
