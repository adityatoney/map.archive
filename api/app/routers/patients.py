"""Patient router."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_db
from app.models.patient import Patient
from app.models.session import ScanSession
from app.models.trend import ConditionTrend
from app.utils.auth import get_current_user
from app.utils.encryption import decrypt_phi

router = APIRouter()


class PatientSummary(BaseModel):
    id: str
    first_name: str
    last_name: str
    middle_name: str | None
    age: int | None
    birthday: str | None
    blood_group: str | None

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    id: str
    scan_date: str
    report_generated_at: str | None = None
    report_type: str
    analysis_status: str
    organ_system: str | None
    entry_count: int


class PatientHistoryResponse(BaseModel):
    patient: PatientSummary
    sessions: list[SessionSummary]
    total_sessions: int


@router.get("/", response_model=list[PatientSummary])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List all patients."""
    result = await db.execute(select(Patient).order_by(Patient.created_at.desc()))
    patients = result.scalars().all()

    return [
        PatientSummary(
            id=str(p.id),
            first_name=decrypt_phi(p.encrypted_first_name),
            last_name=decrypt_phi(p.encrypted_last_name),
            middle_name=decrypt_phi(p.encrypted_middle_name) if p.encrypted_middle_name else None,
            age=p.age,
            birthday=p.birthday,
            blood_group=p.blood_group,
        )
        for p in patients
    ]


@router.get("/{patient_id}/history", response_model=PatientHistoryResponse)
async def get_patient_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get all scan sessions for a patient."""
    result = await db.execute(
        select(Patient)
        .options(selectinload(Patient.sessions).selectinload(ScanSession.entries))
        .where(Patient.id == uuid.UUID(patient_id))
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    sessions = sorted(patient.sessions, key=lambda s: s.scan_date, reverse=True)

    return PatientHistoryResponse(
        patient=PatientSummary(
            id=str(patient.id),
            first_name=decrypt_phi(patient.encrypted_first_name),
            last_name=decrypt_phi(patient.encrypted_last_name),
            middle_name=decrypt_phi(patient.encrypted_middle_name)
            if patient.encrypted_middle_name
            else None,
            age=patient.age,
            birthday=patient.birthday,
            blood_group=patient.blood_group,
        ),
        sessions=[
            SessionSummary(
                id=str(s.id),
                scan_date=s.scan_date.isoformat(),
                report_generated_at=s.report_generated_at.isoformat() if s.report_generated_at else None,
                report_type=s.report_type,
                analysis_status=s.analysis_status,
                organ_system=s.organ_system,
                entry_count=len(s.entries),
            )
            for s in sessions
        ],
        total_sessions=len(sessions),
    )


class TrendResponse(BaseModel):
    condition_name: str
    condition_icd10: str | None
    organ_system: str | None
    trend_direction: str
    trend_slope: float
    sessions_analyzed: int
    first_score: float
    last_score: float
    change_points: list[dict] | None


class PatientTrendsResponse(BaseModel):
    patient_id: str
    trends: list[TrendResponse]
    total_trends: int
    summary: dict


@router.get("/{patient_id}/trends", response_model=PatientTrendsResponse)
async def get_patient_trends(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get temporal trend analysis for a patient's conditions."""
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == uuid.UUID(patient_id))
    )
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await db.execute(
        select(ConditionTrend)
        .where(ConditionTrend.patient_id == uuid.UUID(patient_id))
        .order_by(ConditionTrend.trend_slope.desc())
    )
    trends = result.scalars().all()

    direction_counts = {
        "improving": 0,
        "worsening": 0,
        "stable": 0,
        "volatile": 0,
    }
    for t in trends:
        if t.trend_direction in direction_counts:
            direction_counts[t.trend_direction] += 1

    return PatientTrendsResponse(
        patient_id=patient_id,
        trends=[
            TrendResponse(
                condition_name=t.condition_name,
                condition_icd10=t.condition_icd10,
                organ_system=t.organ_system,
                trend_direction=t.trend_direction,
                trend_slope=t.trend_slope,
                sessions_analyzed=t.sessions_analyzed,
                first_score=t.first_score,
                last_score=t.last_score,
                change_points=t.change_points,
            )
            for t in trends
        ],
        total_trends=len(trends),
        summary=direction_counts,
    )


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete a patient and all associated data (sessions, entries, recovery plans).

    Also cleans up uploaded report files from disk.
    """
    result = await db.execute(
        select(Patient)
        .options(selectinload(Patient.sessions))
        .where(Patient.id == uuid.UUID(patient_id))
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Clean up uploaded files from disk
    for session in patient.sessions:
        if session.raw_report_url and os.path.isfile(session.raw_report_url):
            try:
                os.remove(session.raw_report_url)
            except OSError:
                pass  # Best effort cleanup

    # Delete patient — cascades to sessions, entries, recovery plans, trends
    await db.delete(patient)
    await db.flush()

    return {"detail": f"Patient {patient_id} and all associated data deleted"}
