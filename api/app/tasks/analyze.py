"""Celery task for the full analysis pipeline.

Pipeline: load entries → normalize (ICD-10/SNOMED/FMA) → embed →
cluster → risk score → generate recovery plan → update DB.
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
    from app.services.clusterer import ClustererService
    from app.services.embedder import EmbedderService
    from app.services.normalizer import NormalizerService
    from app.services.recovery_planner import RecoveryPlannerService
    from app.services.risk_engine import RiskEngineService

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

            # Step 5: Risk scoring
            risk_engine = RiskEngineService()
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

            for entry in entries:
                tier = await risk_engine.compute_entry_risk(
                    {"score": entry.score}
                )
                entry.risk_tier = tier

            organ_risks = await risk_engine.compute_organ_risk(entry_dicts)
            logger.info("Risk scoring complete for session %s", session_id)

            # Step 5b: Query knowledge graph for interventions
            from app.services.graph_client import GraphClient

            graph_client = GraphClient()
            icd_list = list(
                set(e.condition_icd10 for e in entries if e.condition_icd10)
            )
            graph_interventions: list[dict] = []
            try:
                graph_nutritional = await graph_client.find_interventions(icd_list)
                graph_lifestyle = await graph_client.find_lifestyle_interventions(
                    icd_list
                )
                graph_interventions = graph_nutritional + [
                    {**li, "type": "lifestyle"} for li in graph_lifestyle
                ]
                logger.info(
                    "Knowledge graph returned %d interventions for session %s",
                    len(graph_interventions),
                    session_id,
                )
            except Exception as kg_err:
                logger.warning(
                    "Knowledge graph query failed (non-fatal): %s", kg_err
                )
            finally:
                graph_client.close()

            # Step 6: Generate recovery plan
            planner = RecoveryPlannerService()
            plan_data = await planner.generate_plan(
                session_id=session_id,
                patient_id=str(session.patient_id),
                entries=entry_dicts,
                organ_risks=organ_risks,
                clusters=cluster_result,
                graph_interventions=graph_interventions or None,
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
                recommended_interventions=plan_data["recommended_interventions"],
                lifestyle_recommendations=plan_data["lifestyle_recommendations"],
                nutritional_recommendations=plan_data["nutritional_recommendations"],
                monitoring_plan=plan_data["monitoring_plan"],
                disclaimer=plan_data["disclaimer"],
            )
            db.add(recovery_plan)

            # Step 7: Update session status
            session.analysis_status = "completed"

            await db.commit()
            logger.info(
                "Analysis pipeline completed for session %s (embedding_source=%s)",
                session_id,
                session.embedding_source,
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
