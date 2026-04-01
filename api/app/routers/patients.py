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
                report_type=s.report_type,
                analysis_status=s.analysis_status,
                organ_system=s.organ_system,
                entry_count=len(s.entries),
            )
            for s in sessions
        ],
        total_sessions=len(sessions),
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
