"""Recovery plan generator — produces structured recovery recommendations.

Uses knowledge graph interventions for evidence-based recommendations
and Claude Agent SDK for LLM-powered plain-language summaries.
Falls back to template-based output when LLM is unavailable.
"""

import asyncio
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
        trends: list[dict] | None = None,
        config=None,
        graph_connectivity: dict | None = None,
    ) -> dict[str, Any]:
        """Generate a complete recovery plan.

        Args:
            session_id: Scan session UUID
            patient_id: Patient UUID
            entries: All scan entries with scores and metadata
            organ_risks: Per-organ risk assessments from RiskEngine
            clusters: Clustering results (optional)
            graph_interventions: Knowledge graph interventions (optional)
            trends: Temporal trend data (optional)
            config: Active RiskConfig (optional, uses defaults if None)
            graph_connectivity: Per-ICD10 connectivity metrics from KG (optional)

        Returns:
            Dict matching the RecoveryPlan model fields
        """
        priority_conditions = self._identify_priority_conditions(
            entries, config, graph_connectivity
        )
        organ_breakdown = self._build_organ_breakdown(organ_risks)
        interventions = self._generate_interventions(
            entries, organ_risks, graph_interventions
        )
        lifestyle = self._generate_lifestyle_recommendations(entries, organ_risks)
        nutritional = self._generate_nutritional_recommendations(entries, organ_risks)
        monitoring = self._generate_monitoring_plan(entries, organ_risks, config)
        summary = await self._generate_summary(
            entries, organ_risks, priority_conditions, trends
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

    def _identify_priority_conditions(
        self, entries: list[dict], config=None, graph_connectivity: dict | None = None,
    ) -> list[dict]:
        """Identify top priority conditions using score + knowledge graph connectivity.

        1. Deduplicate by condition name — keep the worst score per unique condition
           and aggregate the organ systems / anatomical locations it appears in.
        2. Compute a composite priority score:
           - 70% from risk score (normalized: 0 = lowest risk, 1 = highest risk)
           - 30% from KG connectivity (how many pathways, comorbidities, interventions)
        3. Return top 10, ranked by composite priority.
        """
        from app.utils.risk_tiers import is_score_inverted, score_to_tier

        inverted = is_score_inverted(config)

        # --- Step 1: Deduplicate by condition name ---
        # Group entries by condition_name, track worst score and all locations
        condition_map: dict[str, dict] = {}
        for e in entries:
            name = e.get("condition_name", "Unknown")
            score = e.get("score", 0.0)

            if name not in condition_map:
                condition_map[name] = {
                    "condition_name": name,
                    "worst_score": score,
                    "organ_systems": set(),
                    "anatomical_locations": set(),
                    "icd10": e.get("condition_icd10"),
                    "occurrence_count": 0,
                }

            entry_data = condition_map[name]
            entry_data["occurrence_count"] += 1

            # Track worst score (lowest when inverted, highest when normal)
            if inverted:
                if score < entry_data["worst_score"]:
                    entry_data["worst_score"] = score
            else:
                if score > entry_data["worst_score"]:
                    entry_data["worst_score"] = score

            if e.get("organ_system"):
                entry_data["organ_systems"].add(e["organ_system"])
            if e.get("anatomical_location"):
                entry_data["anatomical_locations"].add(e["anatomical_location"])

        # --- Step 2: Compute composite priority score ---
        conditions = list(condition_map.values())
        for cond in conditions:
            score = cond["worst_score"]

            # Normalize risk component to 0-1 where 1 = highest risk
            if inverted:
                risk_component = 1.0 - score  # low score = high risk → high component
            else:
                risk_component = score  # high score = high risk

            # Knowledge graph connectivity component (0-1)
            kg_component = 0.0
            if graph_connectivity and cond.get("icd10"):
                kg_data = graph_connectivity.get(cond["icd10"], {})
                kg_component = kg_data.get("connectivity_score", 0.0)
                cond["kg_pathways"] = kg_data.get("pathway_count", 0)
                cond["kg_comorbidities"] = kg_data.get("comorbidity_count", 0)
                cond["kg_interventions"] = kg_data.get("intervention_count", 0)

            # Composite: 70% risk, 30% KG connectivity
            cond["priority_score"] = 0.7 * risk_component + 0.3 * kg_component

        # --- Step 3: Sort by composite priority (descending) and return top 10 ---
        conditions.sort(key=lambda c: c["priority_score"], reverse=True)

        results = []
        for i, cond in enumerate(conditions[:10]):
            tier = score_to_tier(cond["worst_score"], config)
            organ_systems = sorted(cond["organ_systems"])
            locations = sorted(cond["anatomical_locations"])

            # Build reasoning string
            reasoning_parts = []
            if cond["occurrence_count"] > 1:
                reasoning_parts.append(
                    f"Found in {cond['occurrence_count']} locations across "
                    f"{len(organ_systems)} organ system(s)"
                )
            if cond.get("kg_pathways", 0) > 0:
                reasoning_parts.append(
                    f"{cond['kg_pathways']} biological pathway(s)"
                )
            if cond.get("kg_comorbidities", 0) > 0:
                reasoning_parts.append(
                    f"{cond['kg_comorbidities']} comorbid condition(s)"
                )

            focus = (
                "Monitor closely and consider specialist consultation"
                if tier in ("high", "critical")
                else "Continue monitoring"
            )

            results.append({
                "rank": i + 1,
                "condition_name": cond["condition_name"],
                "organ_system": ", ".join(organ_systems[:3]) if organ_systems else "Unknown",
                "score": cond["worst_score"],
                "risk_tier": tier,
                "anatomical_location": ", ".join(locations[:3]) if locations else None,
                "occurrence_count": cond["occurrence_count"],
                "priority_score": round(cond["priority_score"], 3),
                "kg_connected": bool(cond.get("kg_pathways", 0) or cond.get("kg_comorbidities", 0)),
                "reasoning": "; ".join(reasoning_parts) if reasoning_parts else None,
                "recommended_focus": focus,
            })

        return results

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
        """Generate structured intervention recommendations."""
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
        self, entries: list[dict], organ_risks: list[dict], config=None
    ) -> dict:
        """Generate a monitoring plan."""
        from app.utils.risk_tiers import is_score_inverted

        inverted = is_score_inverted(config)
        high_risk_organs = [r for r in organ_risks if r["risk_tier"] in ("high", "critical")]

        # Sort by worst conditions first
        sorted_by_risk = sorted(
            entries,
            key=lambda x: x.get("score", 0),
            reverse=not inverted,
        )

        return {
            "recommended_rescan_interval": "4-6 weeks"
            if high_risk_organs
            else "8-12 weeks",
            "focus_areas": [r["organ_system"] for r in high_risk_organs],
            "watch_conditions": [
                e.get("condition_name") for e in sorted_by_risk[:5]
            ],
            "metrics_to_track": [
                "Score changes in high-risk conditions",
                "New conditions appearing",
                "Previously flagged conditions resolving",
            ],
        }

    async def _generate_summary(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        priority_conditions: list[dict],
        trends: list[dict] | None = None,
    ) -> str:
        """Generate a plain-language summary.

        Tries LLM-powered summary via Claude Agent SDK first.
        Falls back to template-based summary if LLM is unavailable.
        """
        llm_summary = await self._generate_summary_llm(
            entries, organ_risks, priority_conditions, trends
        )
        if llm_summary:
            return llm_summary

        # Template fallback
        return self._generate_summary_template(
            entries, organ_risks, priority_conditions, trends
        )

    async def _generate_summary_llm(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        priority_conditions: list[dict],
        trends: list[dict] | None = None,
    ) -> str | None:
        """Generate LLM-powered summary using Claude Agent SDK.

        Uses the claude-agent-sdk Python package. Authentication flows through
        the user's existing Claude Code OAuth login (Max subscription).

        Returns None on failure (triggers template fallback).
        """
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query

            from app.config import get_settings

            settings = get_settings()

            prompt = self._build_summary_prompt(
                entries, organ_risks, priority_conditions, trends
            )

            system_prompt = (
                "You are a medical analytics summarizer for the MedBed Insight platform. "
                "Produce a 2-3 paragraph plain-language summary of scan analysis results. "
                "Be precise about the data — include specific counts and scores. "
                "Never provide medical advice or diagnosis. "
                "Always note that results are from frequency-based scan analysis and should "
                "be discussed with a healthcare professional. Do not use markdown formatting. "
                "Do not use bullet points. Write in flowing paragraphs."
            )

            options = ClaudeAgentOptions(
                model=settings.ANTHROPIC_MODEL,
                system_prompt=system_prompt,
                allowed_tools=[],  # No tools needed — pure text generation
                max_turns=1,
            )

            result_text = ""
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    break

            if result_text and len(result_text) > 50:
                logger.info(
                    "LLM summary generated successfully (%d chars)",
                    len(result_text),
                )
                return result_text

            logger.warning("LLM returned empty or short summary, falling back to template")
            return None

        except ImportError:
            logger.info(
                "claude-agent-sdk not available; using template summary"
            )
            return None
        except Exception as e:
            logger.warning(
                "Claude Agent SDK summary generation failed: %s. "
                "Falling back to template.",
                e,
            )
            return None

    def _build_summary_prompt(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        priority_conditions: list[dict],
        trends: list[dict] | None = None,
    ) -> str:
        """Build a structured prompt for LLM summary generation."""
        parts = [
            f"Summarize these MedBed scan analysis results:\n\n",
            f"- {len(entries)} conditions analyzed across {len(organ_risks)} organ systems\n",
        ]

        # High-risk organs
        high_risk = [
            r for r in organ_risks if r["risk_tier"] in ("high", "critical")
        ]
        if high_risk:
            organs_str = ", ".join(
                f"{r['organ_system']} ({r['risk_tier']}, score: {r['risk_score']})"
                for r in high_risk
            )
            parts.append(f"- High/critical risk organs: {organs_str}\n")

        # Moderate risk
        moderate_risk = [
            r for r in organ_risks if r["risk_tier"] == "moderate"
        ]
        if moderate_risk:
            parts.append(
                f"- {len(moderate_risk)} organ system(s) at moderate risk\n"
            )

        # Top conditions
        if priority_conditions:
            parts.append("- Top priority conditions:\n")
            for pc in priority_conditions[:5]:
                parts.append(
                    f"  - {pc['condition_name']} "
                    f"(score: {pc['score']:.3f}, {pc['organ_system']})\n"
                )

        # Trends
        if trends:
            worsening = [
                t for t in trends if t["trend_direction"] == "worsening"
            ]
            improving = [
                t for t in trends if t["trend_direction"] == "improving"
            ]
            volatile = [
                t for t in trends if t["trend_direction"] == "volatile"
            ]
            stable = [
                t for t in trends if t["trend_direction"] == "stable"
            ]

            parts.append(
                f"\n- Temporal trends ({len(trends)} conditions tracked):\n"
            )
            if worsening:
                parts.append(
                    f"  - Worsening: {', '.join(t['condition_name'] for t in worsening[:5])}\n"
                )
            if improving:
                parts.append(
                    f"  - Improving: {', '.join(t['condition_name'] for t in improving[:5])}\n"
                )
            if volatile:
                parts.append(
                    f"  - Volatile: {', '.join(t['condition_name'] for t in volatile[:3])}\n"
                )
            parts.append(
                f"  - Summary: {len(improving)} improving, "
                f"{len(worsening)} worsening, "
                f"{len(stable)} stable, "
                f"{len(volatile)} volatile\n"
            )

        return "".join(parts)

    def _generate_summary_template(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        priority_conditions: list[dict],
        trends: list[dict] | None = None,
    ) -> str:
        """Generate a template-based summary (fallback)."""
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

        # Add trend information if available
        if trends:
            worsening = [t for t in trends if t["trend_direction"] == "worsening"]
            improving = [t for t in trends if t["trend_direction"] == "improving"]
            if worsening:
                summary_parts.append(
                    f"Temporal analysis shows {len(worsening)} condition(s) "
                    f"with worsening trends that may need attention. "
                )
            if improving:
                summary_parts.append(
                    f"{len(improving)} condition(s) show improving trends. "
                )

        summary_parts.append(
            "These patterns are derived from frequency-based scan data analysis "
            "and should be discussed with a qualified healthcare professional "
            "for proper interpretation and guidance."
        )

        return "".join(summary_parts)

    @staticmethod
    def _score_to_tier(score: float, config=None) -> str:
        from app.utils.risk_tiers import score_to_tier
        return score_to_tier(score, config)
