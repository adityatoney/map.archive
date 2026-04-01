"""Recovery plan generator — produces structured recovery recommendations.

Stub implementation for Phase 1 with template-based output.
Phase 2+: Will use knowledge graph interventions + Anthropic API for
plain-language summary generation.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.recovery import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)


class RecoveryPlannerService:
    """Generate structured recovery plans from analysis results."""

    async def generate_plan(
        self,
        session_id: str,
        patient_id: str,
        entries: list[dict],
        organ_risks: list[dict],
        clusters: dict | None = None,
        graph_interventions: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Generate a complete recovery plan.

        Args:
            session_id: Scan session UUID
            patient_id: Patient UUID
            entries: All scan entries with scores and metadata
            organ_risks: Per-organ risk assessments from RiskEngine
            clusters: Clustering results (optional)
            graph_interventions: Knowledge graph interventions (optional)

        Returns:
            Dict matching the RecoveryPlan model fields
        """
        priority_conditions = self._identify_priority_conditions(entries)
        organ_breakdown = self._build_organ_breakdown(organ_risks)
        interventions = self._generate_interventions(
            entries, organ_risks, graph_interventions
        )
        lifestyle = self._generate_lifestyle_recommendations(entries, organ_risks)
        nutritional = self._generate_nutritional_recommendations(entries, organ_risks)
        monitoring = self._generate_monitoring_plan(entries, organ_risks)
        summary = self._generate_summary(
            entries, organ_risks, priority_conditions
        )

        return {
            "session_id": session_id,
            "patient_id": patient_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "organ_system_breakdown": organ_breakdown,
            "priority_conditions": priority_conditions,
            "recommended_interventions": interventions,
            "lifestyle_recommendations": lifestyle,
            "nutritional_recommendations": nutritional,
            "monitoring_plan": monitoring,
            "disclaimer": MEDICAL_DISCLAIMER,
        }

    def _identify_priority_conditions(self, entries: list[dict]) -> list[dict]:
        """Identify top 5 conditions by risk score."""
        sorted_entries = sorted(
            entries, key=lambda e: e.get("score", 0), reverse=True
        )
        return [
            {
                "rank": i + 1,
                "condition_name": e.get("condition_name", "Unknown"),
                "organ_system": e.get("organ_system", "Unknown"),
                "score": e.get("score", 0.0),
                "risk_tier": self._score_to_tier(e.get("score", 0.0)),
                "anatomical_location": e.get("anatomical_location"),
                "recommended_focus": "Monitor closely and consider specialist consultation"
                if e.get("score", 0) >= 0.45
                else "Continue monitoring",
            }
            for i, e in enumerate(sorted_entries[:5])
        ]

    def _build_organ_breakdown(self, organ_risks: list[dict]) -> list[dict]:
        """Build per-organ-system analysis summary."""
        return [
            {
                "organ_system": r["organ_system"],
                "risk_tier": r["risk_tier"],
                "risk_score": r["risk_score"],
                "condition_count": r["condition_count"],
                "summary": f"{r['organ_system']} shows {r['risk_tier']} risk "
                f"with {r['condition_count']} conditions detected. "
                f"Primary concern: {r.get('recommended_focus', 'general monitoring')}.",
            }
            for r in organ_risks
        ]

    def _generate_interventions(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        graph_interventions: list[dict] | None,
    ) -> list[dict]:
        """Generate structured intervention recommendations.

        Phase 1: Template-based. Phase 2+: Knowledge graph-driven.
        """
        interventions = []

        # High-risk organ systems get specialist referral
        for risk in organ_risks:
            if risk["risk_tier"] in ("high", "critical"):
                interventions.append(
                    {
                        "intervention": f"Specialist consultation for {risk['organ_system']}",
                        "category": "specialist_referral",
                        "targets": risk.get("contributing_factors", []),
                        "evidence_level": "strong",
                        "priority": "immediate",
                        "reasoning": f"{risk['organ_system']} shows {risk['risk_tier']} "
                        f"risk (score: {risk['risk_score']}) with "
                        f"{risk['condition_count']} conditions flagged.",
                    }
                )

        # General monitoring for moderate risk
        for risk in organ_risks:
            if risk["risk_tier"] == "moderate":
                interventions.append(
                    {
                        "intervention": f"Targeted monitoring for {risk['organ_system']}",
                        "category": "monitoring",
                        "targets": risk.get("contributing_factors", []),
                        "evidence_level": "moderate",
                        "priority": "short_term",
                        "reasoning": f"{risk['organ_system']} shows moderate risk. "
                        f"Regular monitoring may help track progression.",
                    }
                )

        # Add knowledge graph interventions if available
        if graph_interventions:
            for gi in graph_interventions[:15]:
                gi_type = gi.get("type", "nutritional")
                conditions_supported = gi.get("conditions_supported", 0)
                conditions_addressed = gi.get("conditions_addressed", 0)
                count = conditions_supported or conditions_addressed or 0
                targets = gi.get("conditions", gi.get("targets", []))

                # Use real evidence level from graph when available
                evidence = gi.get("evidence_level", "emerging")

                # Determine category and priority based on type
                if gi_type == "lifestyle":
                    category = "lifestyle"
                    priority = "ongoing"
                    reasoning = (
                        f"Knowledge graph indicates this lifestyle intervention "
                        f"addresses {count} condition(s): "
                        f"{', '.join(targets[:3]) if targets else 'multiple conditions'}."
                    )
                else:
                    category = "nutritional"
                    priority = "short_term" if evidence == "strong" else "ongoing"
                    reasoning = (
                        f"Knowledge graph links this nutritional factor to "
                        f"{count} condition(s): "
                        f"{', '.join(targets[:3]) if targets else 'multiple conditions'}. "
                        f"Evidence level: {evidence}."
                    )

                interventions.append(
                    {
                        "intervention": gi.get("intervention", ""),
                        "category": category,
                        "targets": targets if isinstance(targets, list) else [],
                        "evidence_level": evidence,
                        "priority": priority,
                        "reasoning": reasoning,
                    }
                )

        return interventions

    def _generate_lifestyle_recommendations(
        self, entries: list[dict], organ_risks: list[dict]
    ) -> list[dict]:
        """Generate lifestyle recommendations based on detected patterns."""
        recommendations = [
            {
                "recommendation": "Regular physical activity appropriate for current health status",
                "category": "exercise",
                "evidence_level": "strong",
                "relevance": "General wellness support for all detected conditions",
            },
            {
                "recommendation": "Stress management through relaxation techniques",
                "category": "stress_management",
                "evidence_level": "strong",
                "relevance": "May support recovery across multiple organ systems",
            },
            {
                "recommendation": "Consistent sleep schedule (7-9 hours)",
                "category": "sleep",
                "evidence_level": "strong",
                "relevance": "Foundation for immune and metabolic recovery",
            },
        ]

        # Add organ-system-specific recommendations
        organ_names = [r["organ_system"] for r in organ_risks if r["risk_tier"] != "low"]
        if any("DIGESTIVE" in o for o in organ_names):
            recommendations.append(
                {
                    "recommendation": "Anti-inflammatory diet with emphasis on gut health",
                    "category": "nutrition",
                    "evidence_level": "moderate",
                    "relevance": "Digestive system conditions detected — dietary changes may help",
                }
            )
        if any("CARDIOVASCULAR" in o for o in organ_names):
            recommendations.append(
                {
                    "recommendation": "Cardiovascular exercise and heart-healthy nutrition",
                    "category": "exercise",
                    "evidence_level": "strong",
                    "relevance": "Cardiovascular conditions detected",
                }
            )

        return recommendations

    def _generate_nutritional_recommendations(
        self, entries: list[dict], organ_risks: list[dict]
    ) -> list[dict]:
        """Generate nutritional recommendations."""
        return [
            {
                "recommendation": "Increase omega-3 fatty acid intake",
                "category": "supplement",
                "evidence_level": "moderate",
                "relevance": "Anti-inflammatory support",
            },
            {
                "recommendation": "Ensure adequate vitamin D levels",
                "category": "supplement",
                "evidence_level": "moderate",
                "relevance": "Immune and bone health support",
            },
            {
                "recommendation": "Probiotics for gut microbiome support",
                "category": "supplement",
                "evidence_level": "moderate",
                "relevance": "Digestive and immune system support",
            },
        ]

    def _generate_monitoring_plan(
        self, entries: list[dict], organ_risks: list[dict]
    ) -> dict:
        """Generate a monitoring plan."""
        high_risk_organs = [r for r in organ_risks if r["risk_tier"] in ("high", "critical")]
        moderate_risk_organs = [r for r in organ_risks if r["risk_tier"] == "moderate"]

        return {
            "recommended_rescan_interval": "4-6 weeks"
            if high_risk_organs
            else "8-12 weeks",
            "focus_areas": [r["organ_system"] for r in high_risk_organs],
            "watch_conditions": [
                e.get("condition_name")
                for e in sorted(entries, key=lambda x: x.get("score", 0), reverse=True)[:5]
            ],
            "metrics_to_track": [
                "Score changes in high-risk conditions",
                "New conditions appearing",
                "Previously flagged conditions resolving",
            ],
        }

    def _generate_summary(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        priority_conditions: list[dict],
    ) -> str:
        """Generate a plain-language summary.

        Phase 1: Template-based. Phase 2+: LLM-generated via Anthropic API.
        """
        total = len(entries)
        high_risk = [r for r in organ_risks if r["risk_tier"] in ("high", "critical")]
        moderate_risk = [r for r in organ_risks if r["risk_tier"] == "moderate"]

        summary_parts = [
            f"This analysis reviewed {total} conditions across "
            f"{len(organ_risks)} organ systems. ",
        ]

        if high_risk:
            organs = ", ".join(r["organ_system"] for r in high_risk)
            summary_parts.append(
                f"The following organ systems show elevated risk patterns that "
                f"may warrant closer attention: {organs}. "
            )

        if priority_conditions:
            top = priority_conditions[0]
            summary_parts.append(
                f"The highest-scoring condition detected is "
                f"{top['condition_name']} (score: {top['score']:.3f}) "
                f"in {top['organ_system']}. "
            )

        if moderate_risk:
            summary_parts.append(
                f"{len(moderate_risk)} organ system(s) show moderate risk "
                f"patterns that may benefit from monitoring. "
            )

        summary_parts.append(
            "These patterns are derived from frequency-based scan data analysis "
            "and should be discussed with a qualified healthcare professional "
            "for proper interpretation and guidance."
        )

        return "".join(summary_parts)

    @staticmethod
    def _score_to_tier(score: float) -> str:
        if score >= 0.75:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.25:
            return "moderate"
        return "low"
