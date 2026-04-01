"""Recovery plan router."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.recovery import MEDICAL_DISCLAIMER, RecoveryPlan
from app.utils.auth import get_current_user

router = APIRouter()


class RecoveryPlanResponse(BaseModel):
    id: str
    session_id: str
    patient_id: str
    generated_at: str
    summary: str | None
    organ_system_breakdown: Any | None
    priority_conditions: Any | None
    recommended_interventions: Any | None
    lifestyle_recommendations: Any | None
    nutritional_recommendations: Any | None
    monitoring_plan: Any | None
    disclaimer: str

    model_config = {"from_attributes": True}


@router.get("/{session_id}", response_model=RecoveryPlanResponse)
async def get_recovery_plan(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get the recovery plan for a scan session."""
    result = await db.execute(
        select(RecoveryPlan).where(
            RecoveryPlan.session_id == uuid.UUID(session_id)
        )
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Recovery plan not yet generated for this session. "
            "Trigger analysis first via POST /api/v1/reports/{session_id}/analyze",
        )

    return RecoveryPlanResponse(
        id=str(plan.id),
        session_id=str(plan.session_id),
        patient_id=str(plan.patient_id),
        generated_at=plan.generated_at.isoformat(),
        summary=plan.summary,
        organ_system_breakdown=plan.organ_system_breakdown,
        priority_conditions=plan.priority_conditions,
        recommended_interventions=plan.recommended_interventions,
        lifestyle_recommendations=plan.lifestyle_recommendations,
        nutritional_recommendations=plan.nutritional_recommendations,
        monitoring_plan=plan.monitoring_plan,
        disclaimer=plan.disclaimer or MEDICAL_DISCLAIMER,
    )
