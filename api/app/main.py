"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Medical Analytics Platform API",
        description="Medical analytics platform for frequency-based body scan reports",
        version="0.1.0",
        debug=settings.DEBUG,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:10513",
            "http://localhost:10517",
            "http://localhost:10511",
            "http://127.0.0.1:10513",
            "http://127.0.0.1:10517",
            "http://127.0.0.1:10511",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from app.routers import admin, auth, clinical, reports, patients, insights, recovery, compare, graph

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(patients.router, prefix="/api/v1/patients", tags=["patients"])
    app.include_router(insights.router, prefix="/api/v1/insights", tags=["insights"])
    app.include_router(recovery.router, prefix="/api/v1/recovery", tags=["recovery"])
    app.include_router(compare.router, prefix="/api/v1/reports", tags=["compare"])
    app.include_router(clinical.router, prefix="/api/v1/clinical", tags=["clinical"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        health = {"status": "ok", "services": {}}

        # Check database
        try:
            from sqlalchemy import text
            from app.models.base import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            health["services"]["db"] = "ok"
        except Exception as e:
            health["services"]["db"] = f"error: {str(e)}"
            health["status"] = "degraded"

        # Check Redis
        try:
            import redis as redis_lib

            r = redis_lib.from_url(settings.REDIS_URL)
            r.ping()
            health["services"]["redis"] = "ok"
        except Exception as e:
            health["services"]["redis"] = f"error: {str(e)}"
            health["status"] = "degraded"

        # Check ML service (optional — behind profiles: ml)
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                ml_resp = await client.get(f"{settings.ML_SERVICE_URL}/health")
                ml_data = ml_resp.json()
                health["services"]["ml"] = (
                    "ok (model loaded)" if ml_data.get("model_loaded")
                    else "ok (model not loaded)"
                )
        except Exception:
            health["services"]["ml"] = "unavailable"

        # Check Neo4j (optional)
        if settings.NEO4J_ENABLED:
            try:
                from neo4j import GraphDatabase

                driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
                driver.verify_connectivity()
                driver.close()
                health["services"]["neo4j"] = "ok"
            except Exception as e:
                health["services"]["neo4j"] = f"unavailable: {str(e)}"
                # Neo4j being down is acceptable — graceful degradation
        else:
            health["services"]["neo4j"] = "disabled"

        return health

    @app.get("/")
    async def root():
        return {
            "name": "Medical Analytics Platform API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    logger.info(
        "Medical Analytics Platform API started (environment=%s, mock_mode=%s)",
        settings.ENVIRONMENT,
        settings.is_mock_mode,
    )

    return app
