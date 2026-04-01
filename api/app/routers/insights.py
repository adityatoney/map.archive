"""Insights router — diagnostic patterns and knowledge graph data."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_db
from app.models.entry import ScanEntry
from app.models.session import ScanSession
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ClusterInfo(BaseModel):
    cluster_id: int
    conditions: list[str]
    avg_score: float
    risk_tier: str | None
    shared_pathways: list[str]
    confidence: float


class PatternCard(BaseModel):
    pattern_name: str
    member_conditions: list[str]
    shared_pathways: list[str]
    confidence_score: float
    description: str


class InsightsResponse(BaseModel):
    session_id: str
    analysis_status: str
    clusters: list[ClusterInfo]
    patterns: list[PatternCard]
    risk_summary: dict
    umap_coords: list[list[float]] | None = None
    embedding_source: str | None = None
    disclaimer: str


DISCLAIMER = (
    "MedBed Insight is an analytical exploration tool. Patterns shown are "
    "algorithmically detected correlations and do not constitute medical diagnosis. "
    "Always consult a qualified healthcare professional."
)


@router.get("/{session_id}", response_model=InsightsResponse)
async def get_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get generated insights for a scan session."""
    result = await db.execute(
        select(ScanSession)
        .options(selectinload(ScanSession.entries))
        .where(ScanSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    entries = session.entries

    # Build cluster info from entries that have been clustered
    clusters_map: dict[int, list[ScanEntry]] = {}
    for entry in entries:
        cid = entry.cluster_id if entry.cluster_id is not None else 0
        clusters_map.setdefault(cid, []).append(entry)

    clusters = []
    for cid, cluster_entries in clusters_map.items():
        avg_score = sum(e.score for e in cluster_entries) / len(cluster_entries)
        risk_tiers = [e.risk_tier for e in cluster_entries if e.risk_tier]
        dominant_risk = max(set(risk_tiers), key=risk_tiers.count) if risk_tiers else None

        clusters.append(
            ClusterInfo(
                cluster_id=cid,
                conditions=[e.condition_name for e in cluster_entries],
                avg_score=round(avg_score, 3),
                risk_tier=dominant_risk,
                shared_pathways=[],  # Populated below from KG
                confidence=0.5 if session.analysis_status == "completed" else 0.0,
            )
        )

    # --- Knowledge Graph Integration ---
    # Enrich clusters with shared pathways and build pattern cards
    patterns: list[PatternCard] = []
    try:
        from app.services.graph_client import GraphClient

        graph_client = GraphClient()

        # Populate shared_pathways per cluster
        for cluster_info in clusters:
            # Get ICD-10 codes for entries in this cluster
            cluster_icds: list[str] = []
            for entry in clusters_map.get(cluster_info.cluster_id, []):
                if entry.condition_icd10 and entry.condition_icd10 not in cluster_icds:
                    cluster_icds.append(entry.condition_icd10)

            # Query shared pathways between first pair of ICD codes
            if len(cluster_icds) >= 2:
                pathway_names: set[str] = set()
                # Check pairs (limit to first 3 pairs to avoid N^2 queries)
                pairs_checked = 0
                for i in range(len(cluster_icds)):
                    for j in range(i + 1, len(cluster_icds)):
                        if pairs_checked >= 3:
                            break
                        shared = await graph_client.find_shared_pathways(
                            cluster_icds[i], cluster_icds[j]
                        )
                        for sp in shared:
                            pathway_names.add(sp["pathway"])
                        pairs_checked += 1
                    if pairs_checked >= 3:
                        break
                cluster_info.shared_pathways = sorted(pathway_names)

            # Boost confidence if pathways found (dual-signal: semantic + graph)
            if cluster_info.shared_pathways:
                cluster_info.confidence = min(
                    0.5 + 0.1 * len(cluster_info.shared_pathways), 1.0
                )

        # Build systemic pattern cards
        all_icds = list(
            set(e.condition_icd10 for e in entries if e.condition_icd10)
        )
        if all_icds:
            systemic = await graph_client.find_systemic_patterns(all_icds)
            seen_pairs: set[tuple[str, str]] = set()
            for sp in systemic:
                # Deduplicate A↔B pairs
                pair = tuple(sorted([sp["disease1"], sp["disease2"]]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                pathway_list = sp.get("pathway_names", [])
                patterns.append(
                    PatternCard(
                        pattern_name=f"{sp['disease1']} — {sp['disease2']}",
                        member_conditions=[sp["disease1"], sp["disease2"]],
                        shared_pathways=pathway_list[:5],
                        confidence_score=round(
                            min(sp.get("shared_pathways", 1) / 5.0, 1.0), 2
                        ),
                        description=(
                            f"These conditions share {sp.get('shared_pathways', 0)} "
                            f"biological pathway(s): "
                            f"{', '.join(pathway_list[:3])}."
                        ),
                    )
                )

        graph_client.close()
    except Exception as e:
        logger.warning("Knowledge graph enrichment failed (non-fatal): %s", e)

    # Sort patterns by confidence descending
    patterns.sort(key=lambda p: p.confidence_score, reverse=True)

    # Risk summary by organ system
    organ_scores: dict[str, list[float]] = {}
    for entry in entries:
        organ = entry.organ_system or "Unknown"
        organ_scores.setdefault(organ, []).append(entry.score)

    risk_summary = {}
    for organ, scores in organ_scores.items():
        avg = sum(scores) / len(scores)
        risk_summary[organ] = {
            "avg_score": round(avg, 3),
            "condition_count": len(scores),
            "risk_tier": (
                "critical" if avg >= 0.75
                else "high" if avg >= 0.5
                else "moderate" if avg >= 0.25
                else "low"
            ),
        }

    # Extract UMAP coords from cluster metadata if available
    umap_coords = None
    if session.cluster_metadata and "umap_coords" in session.cluster_metadata:
        umap_coords = session.cluster_metadata["umap_coords"]

    return InsightsResponse(
        session_id=session_id,
        analysis_status=session.analysis_status,
        clusters=clusters,
        patterns=patterns,
        risk_summary=risk_summary,
        umap_coords=umap_coords,
        embedding_source=session.embedding_source,
        disclaimer=DISCLAIMER,
    )
