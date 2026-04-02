"""Session comparison router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_db
from app.models.session import ScanSession
from app.utils.auth import get_current_user
from app.utils.risk_tiers import get_active_risk_config, is_score_inverted

router = APIRouter()


class CompareRequest(BaseModel):
    session_id_1: str
    session_id_2: str


class ConditionDelta(BaseModel):
    condition_name: str
    organ_system: str | None
    score_1: float | None
    score_2: float | None
    delta: float | None
    status: str  # "improved", "worsened", "stable", "new", "resolved"


class CompareResponse(BaseModel):
    session_1_id: str
    session_1_date: str
    session_2_id: str
    session_2_date: str
    deltas: list[ConditionDelta]
    organ_system_summary: dict
    new_conditions: list[str]
    resolved_conditions: list[str]


@router.post("/compare", response_model=CompareResponse)
async def compare_sessions(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Compare two scan sessions side-by-side."""
    config = await get_active_risk_config(db)
    inverted = is_score_inverted(config)

    # Load both sessions with entries
    result1 = await db.execute(
        select(ScanSession)
        .options(selectinload(ScanSession.entries))
        .where(ScanSession.id == uuid.UUID(request.session_id_1))
    )
    result2 = await db.execute(
        select(ScanSession)
        .options(selectinload(ScanSession.entries))
        .where(ScanSession.id == uuid.UUID(request.session_id_2))
    )

    session1 = result1.scalar_one_or_none()
    session2 = result2.scalar_one_or_none()

    if not session1:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id_1} not found")
    if not session2:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id_2} not found")

    # Build lookup maps by condition name
    entries1 = {e.condition_name: e for e in session1.entries}
    entries2 = {e.condition_name: e for e in session2.entries}

    all_conditions = set(entries1.keys()) | set(entries2.keys())

    deltas = []
    new_conditions = []
    resolved_conditions = []
    organ_scores: dict[str, dict] = {}

    for condition in sorted(all_conditions):
        e1 = entries1.get(condition)
        e2 = entries2.get(condition)

        score1 = e1.score if e1 else None
        score2 = e2.score if e2 else None
        organ = (e1 or e2).organ_system if (e1 or e2) else None

        if score1 is not None and score2 is not None:
            delta = round(score2 - score1, 4)
            if abs(delta) < 0.01:
                status = "stable"
            elif inverted:
                # Inverted: rising score = healthier = improved
                status = "improved" if delta > 0 else "worsened"
            else:
                # Normal: falling score = healthier = improved
                status = "improved" if delta < 0 else "worsened"
        elif score1 is None:
            delta = None
            status = "new"
            new_conditions.append(condition)
        else:
            delta = None
            status = "resolved"
            resolved_conditions.append(condition)

        deltas.append(
            ConditionDelta(
                condition_name=condition,
                organ_system=organ,
                score_1=score1,
                score_2=score2,
                delta=delta,
                status=status,
            )
        )

        # Aggregate organ system summary
        if organ:
            if organ not in organ_scores:
                organ_scores[organ] = {"scores_1": [], "scores_2": []}
            if score1 is not None:
                organ_scores[organ]["scores_1"].append(score1)
            if score2 is not None:
                organ_scores[organ]["scores_2"].append(score2)

    organ_summary = {}
    for organ, data in organ_scores.items():
        avg1 = sum(data["scores_1"]) / len(data["scores_1"]) if data["scores_1"] else None
        avg2 = sum(data["scores_2"]) / len(data["scores_2"]) if data["scores_2"] else None
        organ_summary[organ] = {
            "avg_score_1": round(avg1, 3) if avg1 else None,
            "avg_score_2": round(avg2, 3) if avg2 else None,
            "delta": round(avg2 - avg1, 3) if avg1 and avg2 else None,
        }

    return CompareResponse(
        session_1_id=str(session1.id),
        session_1_date=session1.scan_date.isoformat(),
        session_2_id=str(session2.id),
        session_2_date=session2.scan_date.isoformat(),
        deltas=deltas,
        organ_system_summary=organ_summary,
        new_conditions=new_conditions,
        resolved_conditions=resolved_conditions,
    )
