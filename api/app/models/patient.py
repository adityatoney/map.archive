"""Patient model with encrypted PHI fields."""

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.session import ScanSession
    from app.models.trend import ConditionTrend
    from app.models.recovery import RecoveryPlan


class Patient(Base, UUIDMixin, TimestampMixin):
    """Patient record. Name fields are Fernet-encrypted at rest."""

    __tablename__ = "patients"

    # Encrypted PHI fields (stored as Fernet ciphertext)
    encrypted_first_name: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_last_name: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_middle_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Non-PHI demographics
    age: Mapped[int | None] = mapped_column(nullable=True)
    birthday: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    sessions: Mapped[list["ScanSession"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    trends: Mapped[list["ConditionTrend"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    recovery_plans: Mapped[list["RecoveryPlan"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
