"""Clinical analysis router — LLM-powered diagnostic reasoning."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.clinical_analysis import ClinicalAnalysis
from app.utils.auth import get_current_user

router = APIRouter()


# ---------- Response Models ----------


class RootSystemResponse(BaseModel):
    organ_system: str
    confidence: str
    reasoning: str
    downstream_effects: list[str]


class CascadeChainResponse(BaseModel):
    chain: list[str]
    mechanism: str
    supporting_pathways: list[str]
    key_conditions: list[str]


class KeyPatternResponse(BaseModel):
    pattern_name: str
    conditions_involved: list[str]
    shared_pathways: list[str]
    clinical_significance: str
    severity: str


class ActionableInsightResponse(BaseModel):
    priority: int
    focus_area: str
    reasoning: str
    supported_by: str


class ClinicalAnalysisResponse(BaseModel):
    id: str
    session_id: str
    generated_at: datetime
    systemic_analysis: str | None
    root_systems: list[RootSystemResponse]
    cascade_chains: list[CascadeChainResponse]
    key_patterns: list[KeyPatternResponse]
    actionable_insights: list[ActionableInsightResponse]
    analysis_source: str
    model_used: str | None
    disclaimer: str


# ---------- Endpoints ----------


@router.get("/{session_id}", response_model=ClinicalAnalysisResponse)
async def get_clinical_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get the LLM-generated clinical analysis for a scan session."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    result = await db.execute(
        select(ClinicalAnalysis).where(ClinicalAnalysis.session_id == sid)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical analysis not found for this session. "
            "The report may not have been analyzed yet.",
        )

    return ClinicalAnalysisResponse(
        id=str(analysis.id),
        session_id=str(analysis.session_id),
        generated_at=analysis.generated_at,
        systemic_analysis=analysis.systemic_analysis,
        root_systems=analysis.root_systems or [],
        cascade_chains=analysis.cascade_chains or [],
        key_patterns=analysis.key_patterns or [],
        actionable_insights=analysis.actionable_insights or [],
        analysis_source=analysis.analysis_source,
        model_used=analysis.model_used,
        disclaimer=analysis.disclaimer,
    )
