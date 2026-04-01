"""Risk stratification engine — computes composite risk scores per organ system.

Stub implementation for Phase 1 with basic scoring. Full implementation will
incorporate trend data, cluster density, and knowledge graph pathway load.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

RISK_TIERS = {
    "low": (0.0, 0.25),
    "moderate": (0.25, 0.5),
    "high": (0.5, 0.75),
    "critical": (0.75, 1.0),
}


def score_to_tier(score: float) -> str:
    """Map a 0-1 score to a risk tier."""
    if score >= 0.75:
        return "critical"
    elif score >= 0.5:
        return "high"
    elif score >= 0.25:
        return "moderate"
    return "low"


class RiskEngineService:
    """Compute composite risk scores per organ system and per entry."""

    async def compute_entry_risk(self, entry: dict) -> str:
        """Compute risk tier for a single entry based on its score.

        Phase 1: Simple score-based tier assignment.
        Phase 2+: Will incorporate trend direction, cluster density, and
        knowledge graph pathway load.
        """
        score = entry.get("score", 0.0)
        return score_to_tier(score)

    async def compute_organ_risk(
        self,
        entries: list[dict],
        trends: list[dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Compute composite risk score per organ system.

        Weighting (Phase 2+):
        - 40% current score severity
        - 25% trend direction
        - 20% cluster density
        - 15% knowledge graph pathway load

        Phase 1: Uses current score severity only.

        Returns:
            List of dicts with keys: organ_system, risk_tier, risk_score,
            condition_count, contributing_factors, recommended_focus
        """
        # Group entries by organ system
        organ_groups: dict[str, list[dict]] = {}
        for entry in entries:
            organ = entry.get("organ_system", "Unknown")
            organ_groups.setdefault(organ, []).append(entry)

        results = []
        for organ, organ_entries in organ_groups.items():
            scores = [e.get("score", 0.0) for e in organ_entries]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            max_score = max(scores) if scores else 0.0

            # Phase 1: risk_score is weighted average favoring high scores
            risk_score = 0.7 * avg_score + 0.3 * max_score
            risk_tier = score_to_tier(risk_score)

            # Find the highest-scoring conditions as contributing factors
            sorted_entries = sorted(organ_entries, key=lambda e: e.get("score", 0), reverse=True)
            top_conditions = [
                e.get("condition_name", "Unknown") for e in sorted_entries[:3]
            ]

            results.append(
                {
                    "organ_system": organ,
                    "risk_tier": risk_tier,
                    "risk_score": round(risk_score, 3),
                    "condition_count": len(organ_entries),
                    "avg_score": round(avg_score, 3),
                    "max_score": round(max_score, 3),
                    "contributing_factors": top_conditions,
                    "recommended_focus": top_conditions[0] if top_conditions else None,
                }
            )

        # Sort by risk score descending
        results.sort(key=lambda r: r["risk_score"], reverse=True)
        return results

    async def compute_overall_wellness(self, entries: list[dict]) -> dict:
        """Compute an overall wellness score from all entries.

        Returns:
            {
                "wellness_score": float (0-1, higher is better),
                "risk_tier": str,
                "total_conditions": int,
                "critical_count": int,
                "high_count": int,
                "moderate_count": int,
                "low_count": int,
            }
        """
        if not entries:
            return {
                "wellness_score": 1.0,
                "risk_tier": "low",
                "total_conditions": 0,
                "critical_count": 0,
                "high_count": 0,
                "moderate_count": 0,
                "low_count": 0,
            }

        scores = [e.get("score", 0.0) for e in entries]
        avg_risk = sum(scores) / len(scores)
        wellness = 1.0 - avg_risk  # Invert: low scores = good wellness

        tier_counts = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
        for s in scores:
            tier_counts[score_to_tier(s)] += 1

        return {
            "wellness_score": round(wellness, 3),
            "risk_tier": score_to_tier(avg_risk),
            "total_conditions": len(entries),
            "critical_count": tier_counts["critical"],
            "high_count": tier_counts["high"],
            "moderate_count": tier_counts["moderate"],
            "low_count": tier_counts["low"],
        }
