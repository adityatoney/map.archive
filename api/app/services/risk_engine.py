"""Risk stratification engine — computes composite risk scores per organ system.

Uses a 4-component weighted formula:
- 40% current score severity
- 25% trend direction
- 20% cluster density
- 15% knowledge graph pathway load

Score interpretation is configurable via RiskConfig (inverted or normal mode).
"""

import logging
from typing import Any

from app.utils.risk_tiers import is_score_inverted, score_to_severity, score_to_tier

logger = logging.getLogger(__name__)

# Composite risk weights
W_SEVERITY = 0.40
W_TREND = 0.25
W_CLUSTER = 0.20
W_PATHWAY = 0.15


def _composite_risk_to_tier(risk_score: float) -> str:
    """Map a composite risk score (0-1, higher=worse) to a tier.

    This always uses "normal" interpretation because the composite formula
    already normalizes severity regardless of raw score direction.
    """
    if risk_score >= 0.75:
        return "critical"
    elif risk_score >= 0.5:
        return "high"
    elif risk_score >= 0.25:
        return "moderate"
    return "low"

# Trend direction → numeric score mapping (higher = more risk contribution)
TREND_DIRECTION_SCORES = {
    "worsening": 1.0,
    "volatile": 0.75,
    "stable": 0.5,
    "improving": 0.0,
}


class RiskEngineService:
    """Compute composite risk scores per organ system and per entry."""

    async def compute_entry_risk(self, entry: dict, config=None) -> str:
        """Compute risk tier for a single entry based on its score.

        Uses simple score-based tier assignment for individual entries.
        Composite scoring applies at the organ-system level.
        """
        score = entry.get("score", 0.0)
        return score_to_tier(score, config)

    async def compute_organ_risk(
        self,
        entries: list[dict],
        trends: list[dict] | None = None,
        cluster_data: dict | None = None,
        pathway_counts: dict[str, int] | None = None,
        config=None,
    ) -> list[dict[str, Any]]:
        """Compute composite risk score per organ system.

        Weighting:
        - 40% current score severity (avg/max blend, normalized to 0-1 risk)
        - 25% trend direction (improving/worsening/stable/volatile)
        - 20% cluster density (conditions in non-noise clusters)
        - 15% knowledge graph pathway load (shared pathway count)

        Returns:
            List of dicts with keys: organ_system, risk_tier, risk_score,
            condition_count, contributing_factors, recommended_focus,
            risk_components
        """
        inverted = is_score_inverted(config)

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

            # Component 1: Severity (40%)
            # Convert to risk magnitude (0-1, higher = more risk)
            if inverted:
                # Inverted: lower raw score = higher risk
                min_score = min(scores) if scores else 0.0
                severity = 1.0 - (0.7 * avg_score + 0.3 * min_score)
            else:
                severity = 0.7 * avg_score + 0.3 * max_score

            # Component 2: Trend (25%)
            trend_score = self._compute_trend_component(organ, trends)

            # Component 3: Cluster density (20%)
            cluster_density = self._compute_cluster_component(
                organ, entries, organ_entries, cluster_data
            )

            # Component 4: KG pathway load (15%)
            pathway_load = self._compute_pathway_component(
                organ, pathway_counts
            )

            # Composite risk score (always 0-1, higher = more risk)
            risk_score = (
                W_SEVERITY * severity
                + W_TREND * trend_score
                + W_CLUSTER * cluster_density
                + W_PATHWAY * pathway_load
            )

            risk_tier = _composite_risk_to_tier(risk_score)

            # Find the most concerning conditions as contributing factors
            # For inverted: lowest raw score = worst; for normal: highest = worst
            sorted_entries = sorted(
                organ_entries,
                key=lambda e: e.get("score", 0),
                reverse=not inverted,
            )
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
                    "recommended_focus": top_conditions[0]
                    if top_conditions
                    else None,
                    "risk_components": {
                        "severity": round(severity, 3),
                        "trend": round(trend_score, 3),
                        "cluster_density": round(cluster_density, 3),
                        "pathway_load": round(pathway_load, 3),
                    },
                }
            )

        # Sort by risk score descending (highest composite risk first)
        results.sort(key=lambda r: r["risk_score"], reverse=True)
        return results

    def _compute_trend_component(
        self, organ: str, trends: list[dict] | None
    ) -> float:
        """Compute trend score for an organ system (0-1).

        Maps each condition's trend direction to a score and averages.
        Defaults to 0.5 (neutral) if no trend data available.
        """
        if not trends:
            return 0.5

        organ_trends = [
            t for t in trends if t.get("organ_system") == organ
        ]
        if not organ_trends:
            return 0.5

        direction_scores = [
            TREND_DIRECTION_SCORES.get(t["trend_direction"], 0.5)
            for t in organ_trends
        ]
        return sum(direction_scores) / len(direction_scores)

    def _compute_cluster_component(
        self,
        organ: str,
        all_entries: list[dict],
        organ_entries: list[dict],
        cluster_data: dict | None,
    ) -> float:
        """Compute cluster density for an organ system (0-1).

        Higher density = more conditions clustered together = systemic concern.
        """
        if not cluster_data or "labels" not in cluster_data:
            return 0.0

        labels = cluster_data["labels"]
        if len(labels) != len(all_entries):
            return 0.0

        # Find indices of this organ's entries in the full entry list
        organ_condition_names = {
            e.get("condition_name") for e in organ_entries
        }
        organ_labels = [
            labels[i]
            for i, e in enumerate(all_entries)
            if e.get("condition_name") in organ_condition_names
        ]

        if not organ_labels:
            return 0.0

        # Count non-noise entries (cluster_id != -1)
        non_noise = [label for label in organ_labels if label != -1]
        return len(non_noise) / max(len(all_entries), 1)

    def _compute_pathway_component(
        self, organ: str, pathway_counts: dict[str, int] | None
    ) -> float:
        """Compute KG pathway load for an organ system (0-1).

        Normalized: 0 pathways = 0.0, 5+ pathways = 1.0
        """
        if not pathway_counts:
            return 0.0

        raw_pathways = pathway_counts.get(organ, 0)
        return min(raw_pathways / 5.0, 1.0)

    async def compute_overall_wellness(
        self, entries: list[dict], config=None
    ) -> dict:
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

        inverted = is_score_inverted(config)
        scores = [e.get("score", 0.0) for e in entries]
        avg_score = sum(scores) / len(scores)

        # Wellness: higher = healthier
        if inverted:
            wellness = avg_score  # High raw score = healthy
        else:
            wellness = 1.0 - avg_score  # Low raw score = healthy

        tier_counts = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
        for s in scores:
            tier_counts[score_to_tier(s, config)] += 1

        # Overall risk tier (invert wellness to get risk magnitude)
        overall_risk = 1.0 - wellness
        overall_tier = _composite_risk_to_tier(overall_risk)

        return {
            "wellness_score": round(wellness, 3),
            "risk_tier": overall_tier,
            "total_conditions": len(entries),
            "critical_count": tier_counts["critical"],
            "high_count": tier_counts["high"],
            "moderate_count": tier_counts["moderate"],
            "low_count": tier_counts["low"],
        }
