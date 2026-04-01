"""Seed script — creates demo data for development.

Usage: python -m app.seed
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base
from app.models.entry import ScanEntry
from app.models.patient import Patient
from app.models.session import ScanSession
from app.models.user import User
from app.utils.auth import hash_password
from app.utils.encryption import encrypt_phi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demo scan entries from a real Med Bed report format
DEMO_ENTRIES_SESSION_1 = [
    {"condition_name": "ANAEMIA", "score": 0.188, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "ATHEROSCLEROSIS", "score": 0.026, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "ATROPHIC GASTRITIS", "score": 0.230, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "BRONCHIAL ASTHMA", "score": 0.300, "organ_system": "01 CORE PRODUCT", "anatomical_location": "CROSS - SECTION OF NECK", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CARDIAC ARRHYTHMIA", "score": 0.410, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHRONIC REFLUX-GASTRITIS", "score": 0.433, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "CHOLESTERIN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHOLESTATIC HEPATOSIS", "score": 0.281, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "INTERLOBULAR BILE DUCT", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "COLITIS", "score": 0.348, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "WALL OF COLON", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "FATTY HEPATOSIS", "score": 0.425, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "HEPATOCYTE", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHRONIC RELAPSING PANCREATITIS", "score": 0.484, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "PANCREATIC DUCT WALL", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "IDIOPATHIC HYPERTENSION", "score": 0.376, "organ_system": "05 CARDIOVASCULAR SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "HYPOTHYROIDISM", "score": 0.140, "organ_system": "07 ENDOCRINE SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "OSTEOPOROSIS", "score": 0.064, "organ_system": "09 OSTEOSKELETAL SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "PROSTATITIS", "score": 0.440, "organ_system": "04 UROGENITAL SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "NEURALGIA", "score": 0.150, "organ_system": "08 NERVOUS SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
]

DEMO_ENTRIES_SESSION_2 = [
    {"condition_name": "ANAEMIA", "score": 0.165, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "ATHEROSCLEROSIS", "score": 0.031, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "ATROPHIC GASTRITIS", "score": 0.210, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "BRONCHIAL ASTHMA", "score": 0.275, "organ_system": "01 CORE PRODUCT", "anatomical_location": "CROSS - SECTION OF NECK", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CARDIAC ARRHYTHMIA", "score": 0.395, "organ_system": "01 CORE PRODUCT", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHRONIC REFLUX-GASTRITIS", "score": 0.450, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "CHOLESTERIN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHOLESTATIC HEPATOSIS", "score": 0.260, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "INTERLOBULAR BILE DUCT", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "COLITIS", "score": 0.310, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "WALL OF COLON", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "FATTY HEPATOSIS", "score": 0.400, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "HEPATOCYTE", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "CHRONIC RELAPSING PANCREATITIS", "score": 0.470, "organ_system": "02 DIGESTIVE SYSTEM", "anatomical_location": "PANCREATIC DUCT WALL", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "IDIOPATHIC HYPERTENSION", "score": 0.350, "organ_system": "05 CARDIOVASCULAR SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "HYPOTHYROIDISM", "score": 0.125, "organ_system": "07 ENDOCRINE SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "OSTEOPOROSIS", "score": 0.058, "organ_system": "09 OSTEOSKELETAL SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "PROSTATITIS", "score": 0.415, "organ_system": "04 UROGENITAL SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
    {"condition_name": "NEURALGIA", "score": 0.130, "organ_system": "08 NERVOUS SYSTEM", "anatomical_location": "BODY OF MAN", "report_section": "A) SIMULAR PROCESSES"},
]


async def seed():
    """Seed the database with demo data."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Create demo user
        demo_user = User(
            email="demo@medbed.local",
            hashed_password=hash_password("demo123"),
            full_name="Demo User",
            is_active=True,
        )
        db.add(demo_user)
        logger.info("Created demo user: demo@medbed.local / demo123")

        # Create demo patient
        patient = Patient(
            encrypted_first_name=encrypt_phi("Ballu"),
            encrypted_last_name=encrypt_phi("Patel"),
            encrypted_middle_name=encrypt_phi(""),
            age=69,
            birthday="01-August-1956",
            address="2242 Peterson Drive",
            blood_group="3",
            phone="4234325034",
        )
        db.add(patient)
        await db.flush()
        logger.info("Created demo patient: Ballu Patel (ID: %s)", patient.id)

        # Session 1 — 6 weeks ago
        session1 = ScanSession(
            patient_id=patient.id,
            scan_date=datetime.now(timezone.utc) - timedelta(weeks=6),
            report_type="pdf",
            analysis_status="completed",
            report_section="A) SIMULAR PROCESSES",
        )
        db.add(session1)
        await db.flush()

        for entry_data in DEMO_ENTRIES_SESSION_1:
            score = entry_data["score"]
            entry = ScanEntry(
                session_id=session1.id,
                condition_name=entry_data["condition_name"],
                anatomical_location=entry_data.get("anatomical_location"),
                organ_system=entry_data.get("organ_system"),
                report_section=entry_data.get("report_section"),
                score=score,
                green_ratio=1.0 - score,
                red_ratio=score,
                risk_tier=(
                    "critical" if score >= 0.75
                    else "high" if score >= 0.5
                    else "moderate" if score >= 0.25
                    else "low"
                ),
            )
            db.add(entry)

        logger.info("Created session 1 with %d entries", len(DEMO_ENTRIES_SESSION_1))

        # Session 2 — current
        session2 = ScanSession(
            patient_id=patient.id,
            scan_date=datetime.now(timezone.utc),
            report_type="pdf",
            analysis_status="completed",
            report_section="A) SIMULAR PROCESSES",
        )
        db.add(session2)
        await db.flush()

        for entry_data in DEMO_ENTRIES_SESSION_2:
            score = entry_data["score"]
            entry = ScanEntry(
                session_id=session2.id,
                condition_name=entry_data["condition_name"],
                anatomical_location=entry_data.get("anatomical_location"),
                organ_system=entry_data.get("organ_system"),
                report_section=entry_data.get("report_section"),
                score=score,
                green_ratio=1.0 - score,
                red_ratio=score,
                risk_tier=(
                    "critical" if score >= 0.75
                    else "high" if score >= 0.5
                    else "moderate" if score >= 0.25
                    else "low"
                ),
            )
            db.add(entry)

        logger.info("Created session 2 with %d entries", len(DEMO_ENTRIES_SESSION_2))

        await db.commit()
        logger.info("Seed data committed successfully!")
        logger.info("  Patient ID: %s", patient.id)
        logger.info("  Session 1 ID: %s", session1.id)
        logger.info("  Session 2 ID: %s", session2.id)


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
