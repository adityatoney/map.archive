"""Temporal trend analyzer — tracks condition score changes across sessions.

Stub implementation for Phase 1. Full implementation will use linear regression
for trend direction and PELT algorithm (ruptures library) for change point detection.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TrendAnalyzerService:
    """Analyze condition score trends across multiple scan sessions."""

    async def analyze_patient_trends(
        self, patient_id: str, sessions_data: list[dict]
    ) -> list[dict[str, Any]]:
        """Compute per-condition trends across sessions.

        Args:
            patient_id: Patient UUID string
            sessions_data: List of session dicts, each with 'session_id',
                          'scan_date', and 'entries' (list of entry dicts)

        Returns:
            List of trend dicts with keys: condition_name, condition_icd10,
            organ_system, trend_direction, trend_slope, sessions_analyzed,
            first_score, last_score, change_points
        """
        if len(sessions_data) < 2:
            logger.info(
                "Not enough sessions for trend analysis (patient=%s, sessions=%d)",
                patient_id,
                len(sessions_data),
            )
            return []

        # Group scores by condition name across sessions
        condition_scores: dict[str, list[dict]] = {}
        for session in sorted(sessions_data, key=lambda s: s.get("scan_date", "")):
            for entry in session.get("entries", []):
                name = entry.get("condition_name", "")
                if name not in condition_scores:
                    condition_scores[name] = []
                condition_scores[name].append(
                    {
                        "session_id": session.get("session_id"),
                        "scan_date": session.get("scan_date"),
                        "score": entry.get("score", 0.0),
                        "icd10": entry.get("condition_icd10"),
                        "organ_system": entry.get("organ_system"),
                    }
                )

        trends = []
        for condition_name, scores in condition_scores.items():
            if len(scores) < 2:
                continue

            first_score = scores[0]["score"]
            last_score = scores[-1]["score"]
            delta = last_score - first_score

            # Simple trend direction
            if abs(delta) < 0.02:
                direction = "stable"
            elif delta < 0:
                direction = "improving"
            else:
                direction = "worsening"

            # Simple slope (score change per session)
            slope = delta / (len(scores) - 1) if len(scores) > 1 else 0.0

            trends.append(
                {
                    "condition_name": condition_name,
                    "condition_icd10": scores[-1].get("icd10"),
                    "organ_system": scores[-1].get("organ_system"),
                    "trend_direction": direction,
                    "trend_slope": round(slope, 4),
                    "sessions_analyzed": len(scores),
                    "first_score": first_score,
                    "last_score": last_score,
                    "change_points": [],  # Phase 2: PELT algorithm
                }
            )

        return trends
