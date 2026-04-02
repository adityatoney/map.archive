"""Celery task for the full analysis pipeline.

Pipeline: load entries → normalize (ICD-10/SNOMED/FMA) → embed →
cluster → trend analysis → composite risk score → KG query →
generate recovery plan → update DB.
"""

import asyncio
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.celery_app import celery
from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_async_session():
    """Create a standalone async session for Celery tasks."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_pipeline(session_id: str):
    """Async implementation of the analysis pipeline."""
    from app.models.recovery import RecoveryPlan
    from app.models.session import ScanSession
    from app.models.trend import ConditionTrend
    from app.services.clusterer import ClustererService
    from app.services.embedder import EmbedderService
    from app.services.graph_client import GraphClient
    from app.services.normalizer import NormalizerService
    from app.services.recovery_planner import RecoveryPlannerService
    from app.services.risk_engine import RiskEngineService
    from app.services.trend_analyzer import TrendAnalyzerService
    from app.utils.risk_tiers import get_active_risk_config, is_score_inverted

    Session = _get_async_session()

    async with Session() as db:
        try:
            # Step 1: Load session and entries
            result = await db.execute(
                select(ScanSession)
                .options(selectinload(ScanSession.entries))
                .where(ScanSession.id == uuid.UUID(session_id))
            )
            session = result.scalar_one_or_none()
            if not session:
                logger.error("Session %s not found", session_id)
                return

            entries = session.entries
            logger.info(
                "Starting analysis pipeline for session %s (%d entries)",
                session_id,
                len(entries),
            )

            # Load risk configuration for score interpretation
            config = await get_active_risk_config(db)

            # Step 2: Normalize conditions (ICD-10, SNOMED, FMA)
            normalizer = NormalizerService()
            for entry in entries:
                codes = await normalizer.normalize_condition(entry.condition_name)
                entry.condition_icd10 = codes.get("icd10")
                entry.condition_snomed = codes.get("snomed")

                if entry.anatomical_location:
                    fma_id = await normalizer.normalize_anatomy(
                        entry.anatomical_location
                    )
                    entry.anatomical_fma_id = fma_id

            logger.info("Normalization complete for session %s", session_id)

            # Step 3: Generate embeddings
            embedder = EmbedderService()

            # Check ML service availability before embedding
            ml_available = await embedder.is_ml_service_available()
            logger.info(
                "ML service available: %s (will use %s embeddings)",
                ml_available,
                "real" if ml_available else "mock",
            )

            texts = [
                embedder._format_entry_text(
                    e.condition_name, e.anatomical_location, e.score
                )
                for e in entries
            ]
            embeddings = await embedder.embed_texts(texts)

            for entry, emb in zip(entries, embeddings):
                entry.embedding_vector = emb

            # Track embedding source on the session
            session.embedding_source = embedder.last_source
            logger.info(
                "Embeddings generated for session %s (source: %s)",
                session_id,
                embedder.last_source,
            )

            # Step 4: Cluster entries
            clusterer = ClustererService()
            condition_names = [e.condition_name for e in entries]
            organ_systems = [e.organ_system for e in entries]
            cluster_result = clusterer.cluster_entries(
                embeddings, condition_names, organ_systems=organ_systems
            )

            for entry, label in zip(entries, cluster_result["labels"]):
                entry.cluster_id = label

            # Persist cluster metadata (UMAP coords, summaries) on session
            session.cluster_metadata = cluster_result

            logger.info("Clustering complete for session %s", session_id)

            # Step 4b: Temporal trend analysis
            trend_analyzer = TrendAnalyzerService()

            # Query all previous completed sessions for this patient
            prev_sessions_result = await db.execute(
                select(ScanSession)
                .options(selectinload(ScanSession.entries))
                .where(
                    ScanSession.patient_id == session.patient_id,
                    ScanSession.analysis_status == "completed",
                    ScanSession.id != session.id,
                )
                .order_by(ScanSession.scan_date)
            )
            prev_sessions = prev_sessions_result.scalars().all()

            # Build sessions_data including previous and current session
            entry_dicts = [
                {
                    "condition_name": e.condition_name,
                    "score": e.score,
                    "organ_system": e.organ_system,
                    "anatomical_location": e.anatomical_location,
                    "condition_icd10": e.condition_icd10,
                }
                for e in entries
            ]

            sessions_data = []
            for s in prev_sessions:
                sessions_data.append(
                    {
                        "session_id": str(s.id),
                        "scan_date": s.scan_date.isoformat()
                        if s.scan_date
                        else "",
                        "entries": [
                            {
                                "condition_name": e.condition_name,
                                "score": e.score,
                                "condition_icd10": e.condition_icd10,
                                "organ_system": e.organ_system,
                            }
                            for e in s.entries
                        ],
                    }
                )

            # Add current session
            sessions_data.append(
                {
                    "session_id": session_id,
                    "scan_date": session.scan_date.isoformat()
                    if session.scan_date
                    else "",
                    "entries": entry_dicts,
                }
            )

            trends = await trend_analyzer.analyze_patient_trends(
                str(session.patient_id),
                sessions_data,
                score_inverted=is_score_inverted(config),
            )

            # Persist trends: delete old, insert new (upsert pattern)
            await db.execute(
                delete(ConditionTrend).where(
                    ConditionTrend.patient_id == session.patient_id
                )
            )
            for t in trends:
                db.add(
                    ConditionTrend(
                        patient_id=session.patient_id,
                        condition_icd10=t["condition_icd10"],
                        condition_name=t["condition_name"],
                        organ_system=t["organ_system"],
                        trend_direction=t["trend_direction"],
                        trend_slope=t["trend_slope"],
                        sessions_analyzed=t["sessions_analyzed"],
                        first_score=t["first_score"],
                        last_score=t["last_score"],
                        change_points=t["change_points"] or None,
                    )
                )

            logger.info(
                "Trend analysis complete for session %s (%d trends)",
                session_id,
                len(trends),
            )

            # Step 5: Risk scoring (with composite formula)
            risk_engine = RiskEngineService()

            for entry in entries:
                tier = await risk_engine.compute_entry_risk(
                    {"score": entry.score}, config=config
                )
                entry.risk_tier = tier
                # Fix green/red ratios based on score mode
                entry.green_ratio = entry.score
                entry.red_ratio = 1.0 - entry.score

            # Step 5a: Query knowledge graph for interventions + pathway counts + connectivity
            graph_client = GraphClient()
            icd_list = list(
                set(e.condition_icd10 for e in entries if e.condition_icd10)
            )
            graph_interventions: list[dict] = []
            pathway_counts: dict[str, int] = {}
            graph_connectivity: dict = {}

            try:
                graph_nutritional = await graph_client.find_interventions(
                    icd_list
                )
                graph_lifestyle = (
                    await graph_client.find_lifestyle_interventions(icd_list)
                )
                graph_interventions = graph_nutritional + [
                    {**li, "type": "lifestyle"} for li in graph_lifestyle
                ]
                logger.info(
                    "Knowledge graph returned %d interventions for session %s",
                    len(graph_interventions),
                    session_id,
                )

                # Query per-condition connectivity for priority ranking
                try:
                    graph_connectivity = await graph_client.get_condition_connectivity(
                        icd_list
                    )
                    logger.info(
                        "Knowledge graph connectivity: %d conditions with KG data",
                        len(graph_connectivity),
                    )
                except Exception as conn_err:
                    logger.warning(
                        "KG connectivity query failed (non-fatal): %s",
                        conn_err,
                    )

                # Precompute pathway counts per organ system for composite risk
                try:
                    systemic = await graph_client.find_systemic_patterns(
                        icd_list
                    )
                    for sp in systemic:
                        for disease_name in [
                            sp["disease1"],
                            sp["disease2"],
                        ]:
                            for e in entry_dicts:
                                if e["condition_name"] == disease_name:
                                    organ = e.get("organ_system", "Unknown")
                                    pathway_counts[organ] = (
                                        pathway_counts.get(organ, 0)
                                        + sp.get("shared_pathways", 0)
                                    )
                except Exception as pw_err:
                    logger.warning(
                        "Pathway count precomputation failed (non-fatal): %s",
                        pw_err,
                    )

            except Exception as kg_err:
                logger.warning(
                    "Knowledge graph query failed (non-fatal): %s", kg_err
                )
            finally:
                graph_client.close()

            # Step 5b: Composite organ risk scoring
            organ_risks = await risk_engine.compute_organ_risk(
                entry_dicts,
                trends=trends,
                cluster_data=cluster_result,
                pathway_counts=pathway_counts,
                config=config,
            )
            logger.info("Risk scoring complete for session %s", session_id)

            # Step 6: Generate recovery plan
            planner = RecoveryPlannerService()
            plan_data = await planner.generate_plan(
                session_id=session_id,
                patient_id=str(session.patient_id),
                entries=entry_dicts,
                organ_risks=organ_risks,
                clusters=cluster_result,
                graph_interventions=graph_interventions or None,
                trends=trends,
                config=config,
                graph_connectivity=graph_connectivity or None,
            )

            # Delete existing recovery plan if re-analyzing
            await db.execute(
                delete(RecoveryPlan).where(
                    RecoveryPlan.session_id == session.id
                )
            )

            # Save recovery plan
            recovery_plan = RecoveryPlan(
                session_id=session.id,
                patient_id=session.patient_id,
                summary=plan_data["summary"],
                organ_system_breakdown=plan_data["organ_system_breakdown"],
                priority_conditions=plan_data["priority_conditions"],
                recommended_interventions=plan_data[
                    "recommended_interventions"
                ],
                lifestyle_recommendations=plan_data[
                    "lifestyle_recommendations"
                ],
                nutritional_recommendations=plan_data[
                    "nutritional_recommendations"
                ],
                monitoring_plan=plan_data["monitoring_plan"],
                disclaimer=plan_data["disclaimer"],
            )
            db.add(recovery_plan)

            # Step 7: Update session status
            session.analysis_status = "completed"

            await db.commit()
            logger.info(
                "Analysis pipeline completed for session %s "
                "(embedding_source=%s, trends=%d)",
                session_id,
                session.embedding_source,
                len(trends),
            )

        except Exception as e:
            logger.exception(
                "Analysis pipeline failed for session %s: %s", session_id, e
            )
            # Update session status to failed
            try:
                session.analysis_status = "failed"
                await db.commit()
            except Exception:
                await db.rollback()
            raise


@celery.task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600)
def run_analysis_pipeline(self, session_id: str):
    """Celery task entry point — runs the async analysis pipeline."""
    try:
        asyncio.run(_run_pipeline(session_id))
    except Exception as e:
        logger.error("Pipeline task failed: %s", e)
        raise self.retry(exc=e)
