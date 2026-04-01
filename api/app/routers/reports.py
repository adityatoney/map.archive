"""Report upload and retrieval router."""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.base import get_db
from app.models.entry import ScanEntry
from app.models.patient import Patient
from app.models.session import ScanSession
from app.services.parser import parse_report
from app.utils.auth import get_current_user
from app.utils.encryption import encrypt_phi, decrypt_phi

router = APIRouter()


# ---------- Schemas ----------

class EntryOut(BaseModel):
    id: str
    condition_name: str
    condition_icd10: str | None
    condition_snomed: str | None
    anatomical_location: str | None
    organ_system: str | None
    report_section: str | None
    score: float
    green_ratio: float | None
    red_ratio: float | None
    marker: str | None
    cluster_id: int | None
    risk_tier: str | None

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    patient_id: str
    scan_date: str
    report_type: str
    analysis_status: str
    organ_system: str | None
    embedding_source: str | None = None
    entry_count: int
    entries: list[EntryOut]

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    session_id: str
    patient_id: str
    entry_count: int
    message: str


class AnalyzeResponse(BaseModel):
    task_id: str
    session_id: str
    status: str


# ---------- Endpoints ----------

@router.post("/upload", response_model=UploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    patient_first_name: str = "Unknown",
    patient_last_name: str = "Patient",
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Upload a new scan report (PDF, CSV, JSON, or image)."""
    settings = get_settings()

    # Determine file type
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_type = file.content_type or ""

    if ext in ("pdf",) or "pdf" in content_type:
        report_type = "pdf"
    elif ext in ("csv",) or "csv" in content_type:
        report_type = "csv"
    elif ext in ("json",) or "json" in content_type:
        report_type = "json"
    elif ext in ("png", "jpg", "jpeg", "tiff", "bmp") or "image" in content_type:
        report_type = "image"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Supported: pdf, csv, json, png, jpg",
        )

    # Save file to uploads directory
    file_bytes = await file.read()
    file_id = str(uuid.uuid4())
    upload_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{ext}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(upload_path, "wb") as f:
        f.write(file_bytes)

    # Parse the report
    try:
        parsed = await parse_report(file_bytes, report_type, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse report: {str(e)}",
        )

    # Extract patient info from parsed data if available
    patient_info = parsed.get("patient_info", {})
    first_name = patient_info.get("first_name", patient_first_name)
    last_name = patient_info.get("last_name", patient_last_name)

    # Find or create patient — deduplicate by matching encrypted name
    encrypted_fn = encrypt_phi(first_name)
    encrypted_ln = encrypt_phi(last_name)

    # Search for existing patient with same name
    existing_patient = None
    if first_name != "Unknown" or last_name != "Patient":
        all_patients = (await db.execute(select(Patient))).scalars().all()
        for p in all_patients:
            try:
                if (
                    decrypt_phi(p.encrypted_first_name) == first_name
                    and decrypt_phi(p.encrypted_last_name) == last_name
                ):
                    existing_patient = p
                    break
            except Exception:
                continue

    if existing_patient:
        patient = existing_patient
        # Update demographics if we have new info
        if patient_info.get("age") and not patient.age:
            patient.age = patient_info["age"]
        if patient_info.get("birthday") and not patient.birthday:
            patient.birthday = patient_info["birthday"]
        if patient_info.get("blood_group") and not patient.blood_group:
            patient.blood_group = patient_info["blood_group"]
        if patient_info.get("address") and not patient.address:
            patient.address = patient_info["address"]
        if patient_info.get("phone") and not patient.phone:
            patient.phone = patient_info["phone"]
    else:
        patient = Patient(
            encrypted_first_name=encrypted_fn,
            encrypted_last_name=encrypted_ln,
            encrypted_middle_name=encrypt_phi(patient_info.get("middle_name", "")),
            age=patient_info.get("age"),
            birthday=patient_info.get("birthday"),
            address=patient_info.get("address"),
            blood_group=patient_info.get("blood_group"),
            phone=patient_info.get("phone"),
        )
        db.add(patient)
        await db.flush()

    # Create scan session
    session = ScanSession(
        patient_id=patient.id,
        scan_date=datetime.now(timezone.utc),
        raw_report_url=upload_path,
        report_type=report_type,
        analysis_status="pending",
    )
    db.add(session)
    await db.flush()

    # Create scan entries
    entries_data = parsed.get("entries", [])
    for entry_data in entries_data:
        score = entry_data.get("score", 0.0)
        entry = ScanEntry(
            session_id=session.id,
            condition_name=entry_data.get("condition_name", "Unknown"),
            anatomical_location=entry_data.get("anatomical_location"),
            organ_system=entry_data.get("organ_system"),
            report_section=entry_data.get("report_section"),
            score=score,
            green_ratio=1.0 - score,  # Derived from score
            red_ratio=score,           # Derived from score
            marker=entry_data.get("marker"),
        )
        db.add(entry)

    await db.flush()

    return UploadResponse(
        session_id=str(session.id),
        patient_id=str(patient.id),
        entry_count=len(entries_data),
        message=f"Successfully parsed {len(entries_data)} entries from {report_type} report",
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get a parsed report with all entries."""
    result = await db.execute(
        select(ScanSession)
        .options(selectinload(ScanSession.entries))
        .where(ScanSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionOut(
        id=str(session.id),
        patient_id=str(session.patient_id),
        scan_date=session.scan_date.isoformat(),
        report_type=session.report_type,
        analysis_status=session.analysis_status,
        organ_system=session.organ_system,
        embedding_source=session.embedding_source,
        entry_count=len(session.entries),
        entries=[
            EntryOut(
                id=str(e.id),
                condition_name=e.condition_name,
                condition_icd10=e.condition_icd10,
                condition_snomed=e.condition_snomed,
                anatomical_location=e.anatomical_location,
                organ_system=e.organ_system,
                report_section=e.report_section,
                score=e.score,
                green_ratio=e.green_ratio,
                red_ratio=e.red_ratio,
                marker=e.marker,
                cluster_id=e.cluster_id,
                risk_tier=e.risk_tier,
            )
            for e in session.entries
        ],
    )


@router.post("/{session_id}/analyze", response_model=AnalyzeResponse)
async def analyze_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Trigger the full NLP + knowledge graph analysis pipeline."""
    result = await db.execute(
        select(ScanSession).where(ScanSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Trigger Celery task
    from app.tasks.analyze import run_analysis_pipeline

    task = run_analysis_pipeline.delay(session_id)

    # Update session status
    session.analysis_status = "processing"
    session.analysis_task_id = task.id
    await db.flush()

    return AnalyzeResponse(
        task_id=task.id,
        session_id=session_id,
        status="processing",
    )


@router.get("/{session_id}/download")
async def download_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Download the original uploaded report file."""
    result = await db.execute(
        select(ScanSession).where(ScanSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.raw_report_url or not os.path.isfile(session.raw_report_url):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    ext = session.report_type or "pdf"
    filename = f"medbed_report_{session_id[:8]}.{ext}"

    return FileResponse(
        path=session.raw_report_url,
        media_type="application/octet-stream",
        filename=filename,
    )
