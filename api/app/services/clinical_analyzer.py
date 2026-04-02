"""Agentic Clinical Analyzer — uses Claude to produce deep diagnostic insights.

Feeds the LLM the full knowledge graph context (shared pathways, comorbidities,
cascade patterns) along with scan data and asks for systemic pattern analysis,
root cause identification, and organ system cascade reasoning.

Falls back to a structured template when LLM is unavailable.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ClinicalAnalyzerService:
    """Generate deep clinical insights using LLM + knowledge graph context."""

    async def analyze(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        graph_interventions: list[dict] | None = None,
        systemic_patterns: list[dict] | None = None,
        graph_connectivity: dict | None = None,
        trends: list[dict] | None = None,
        priority_conditions: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Produce a full clinical analysis with cascade reasoning.

        Returns a dict with:
          - systemic_analysis: str — narrative cascade analysis
          - root_systems: list — identified root organ systems driving issues
          - cascade_chains: list — organ-to-organ cascade pathways
          - key_patterns: list — major clinical patterns identified
          - actionable_insights: list — specific next steps
          - disclaimer: str
        """
        from app.models.recovery import MEDICAL_DISCLAIMER

        # Build the rich context for Claude
        context = self._build_analysis_context(
            entries, organ_risks, graph_interventions,
            systemic_patterns, graph_connectivity, trends,
            priority_conditions,
        )

        # Try LLM analysis first
        llm_result = await self._analyze_with_llm(context)
        if llm_result:
            llm_result["disclaimer"] = MEDICAL_DISCLAIMER
            return llm_result

        # Fallback to template-based analysis
        result = self._analyze_template(
            entries, organ_risks, systemic_patterns, graph_connectivity
        )
        result["disclaimer"] = MEDICAL_DISCLAIMER
        return result

    def _build_analysis_context(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        graph_interventions: list[dict] | None,
        systemic_patterns: list[dict] | None,
        graph_connectivity: dict | None,
        trends: list[dict] | None,
        priority_conditions: list[dict] | None,
    ) -> str:
        """Build a comprehensive context string for Claude with all available data."""
        parts = []

        # --- Section 1: Organ System Risk Overview ---
        parts.append("## ORGAN SYSTEM RISK OVERVIEW")
        parts.append(f"Total conditions analyzed: {len(entries)}")
        parts.append(f"Organ systems assessed: {len(organ_risks)}\n")

        # Group by risk tier
        critical = [r for r in organ_risks if r["risk_tier"] == "critical"]
        high = [r for r in organ_risks if r["risk_tier"] == "high"]
        moderate = [r for r in organ_risks if r["risk_tier"] == "moderate"]
        low = [r for r in organ_risks if r["risk_tier"] == "low"]

        if critical:
            parts.append("CRITICAL RISK:")
            for r in critical:
                parts.append(
                    f"  - {r['organ_system']}: score={r['risk_score']:.3f}, "
                    f"{r['condition_count']} conditions"
                )
                if r.get("contributing_factors"):
                    parts.append(
                        f"    Contributing: {', '.join(str(f) for f in r['contributing_factors'][:5])}"
                    )

        if high:
            parts.append("\nHIGH RISK:")
            for r in high:
                parts.append(
                    f"  - {r['organ_system']}: score={r['risk_score']:.3f}, "
                    f"{r['condition_count']} conditions"
                )
                if r.get("contributing_factors"):
                    parts.append(
                        f"    Contributing: {', '.join(str(f) for f in r['contributing_factors'][:5])}"
                    )

        if moderate:
            parts.append(f"\nMODERATE RISK: {len(moderate)} organ system(s)")
            for r in moderate:
                parts.append(
                    f"  - {r['organ_system']}: score={r['risk_score']:.3f}, "
                    f"{r['condition_count']} conditions"
                )

        if low:
            parts.append(f"\nLOW RISK: {len(low)} organ system(s)")

        # --- Section 2: Conditions by Organ System ---
        parts.append("\n## CONDITIONS BY ORGAN SYSTEM (score 0-1, lower = higher risk)")

        organ_groups: dict[str, list[dict]] = {}
        for e in entries:
            organ = e.get("organ_system", "Unknown")
            organ_groups.setdefault(organ, []).append(e)

        for organ in sorted(organ_groups.keys()):
            conditions = sorted(organ_groups[organ], key=lambda x: x.get("score", 0))
            parts.append(f"\n{organ} ({len(conditions)} conditions):")
            for c in conditions[:10]:  # Top 10 worst per organ
                parts.append(
                    f"  - {c.get('condition_name', '?')} "
                    f"(score: {c.get('score', 0):.3f}, "
                    f"location: {c.get('anatomical_location', 'N/A')})"
                )
            if len(conditions) > 10:
                parts.append(f"  ... and {len(conditions) - 10} more")

        # --- Section 3: Knowledge Graph — Shared Pathways ---
        if systemic_patterns:
            parts.append("\n## KNOWLEDGE GRAPH: SHARED BIOLOGICAL PATHWAYS")
            parts.append(
                "These condition pairs share biological pathways, suggesting "
                "systemic connections:\n"
            )
            seen = set()
            for sp in systemic_patterns[:20]:
                pair = tuple(sorted([sp["disease1"], sp["disease2"]]))
                if pair in seen:
                    continue
                seen.add(pair)
                pathways = sp.get("pathway_names", [])
                parts.append(
                    f"  {sp['disease1']} ↔ {sp['disease2']}: "
                    f"{sp.get('shared_pathways', 0)} shared pathway(s) "
                    f"[{', '.join(pathways[:3])}]"
                )

        # --- Section 4: KG Connectivity ---
        if graph_connectivity:
            parts.append("\n## KNOWLEDGE GRAPH: CONDITION CONNECTIVITY")
            parts.append(
                "Conditions with high connectivity have more biological "
                "pathway links and comorbidity associations:\n"
            )
            sorted_conn = sorted(
                graph_connectivity.items(),
                key=lambda x: x[1].get("connectivity_score", 0),
                reverse=True,
            )
            for icd, data in sorted_conn[:15]:
                parts.append(
                    f"  {icd}: pathways={data.get('pathway_count', 0)}, "
                    f"comorbidities={data.get('comorbidity_count', 0)}, "
                    f"interventions={data.get('intervention_count', 0)}, "
                    f"connectivity={data.get('connectivity_score', 0):.2f}"
                )

        # --- Section 5: Graph Interventions ---
        if graph_interventions:
            parts.append("\n## KNOWLEDGE GRAPH: LINKED INTERVENTIONS")
            nutritional = [g for g in graph_interventions if g.get("type") != "lifestyle"]
            lifestyle = [g for g in graph_interventions if g.get("type") == "lifestyle"]

            if nutritional:
                parts.append("\nNutritional factors with evidence:")
                for n in nutritional[:10]:
                    count = n.get("conditions_supported", 0)
                    targets = n.get("conditions", [])
                    parts.append(
                        f"  - {n.get('intervention', '?')}: "
                        f"supports {count} condition(s) "
                        f"[{', '.join(targets[:3])}]"
                    )
            if lifestyle:
                parts.append("\nLifestyle interventions with evidence:")
                for li in lifestyle[:10]:
                    count = li.get("conditions_addressed", 0)
                    targets = li.get("targets", [])
                    parts.append(
                        f"  - {li.get('intervention', '?')}: "
                        f"addresses {count} condition(s) "
                        f"[{', '.join(targets[:3])}]"
                    )

        # --- Section 6: Trends ---
        if trends:
            parts.append("\n## TEMPORAL TRENDS")
            worsening = [t for t in trends if t.get("trend_direction") == "worsening"]
            improving = [t for t in trends if t.get("trend_direction") == "improving"]
            volatile = [t for t in trends if t.get("trend_direction") == "volatile"]

            if worsening:
                parts.append(f"\nWorsening ({len(worsening)}):")
                for t in worsening[:5]:
                    parts.append(
                        f"  - {t['condition_name']}: "
                        f"slope={t.get('trend_slope', 0):.4f}, "
                        f"first={t.get('first_score', 0):.3f} → last={t.get('last_score', 0):.3f}"
                    )
            if improving:
                parts.append(f"\nImproving ({len(improving)}):")
                for t in improving[:5]:
                    parts.append(
                        f"  - {t['condition_name']}: "
                        f"slope={t.get('trend_slope', 0):.4f}"
                    )
            if volatile:
                parts.append(f"\nVolatile ({len(volatile)}):")
                for t in volatile[:3]:
                    parts.append(f"  - {t['condition_name']}")

        # --- Section 7: Priority Conditions ---
        if priority_conditions:
            parts.append("\n## PRIORITY CONDITIONS (deduplicated, KG-weighted)")
            for pc in priority_conditions[:10]:
                parts.append(
                    f"  {pc['rank']}. {pc['condition_name']} "
                    f"({pc['risk_tier']}, score: {pc['score']:.3f}, "
                    f"locations: {pc.get('occurrence_count', 1)})"
                )
                if pc.get("reasoning"):
                    parts.append(f"     → {pc['reasoning']}")

        return "\n".join(parts)

    async def _analyze_with_llm(self, context: str) -> dict[str, Any] | None:
        """Use Claude to produce structured clinical insights."""
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query

            from app.config import get_settings

            settings = get_settings()

            system_prompt = """You are a clinical analytics engine for the MedBed Insight platform — a frequency-based bioresonance scan analyzer. You are NOT providing medical diagnosis or treatment. You are analyzing scan data patterns to help users understand potential systemic connections.

Your job is to identify PATTERNS in the data:
1. SYSTEMIC CASCADE ANALYSIS: Identify which organ system(s) may be the root driver, and how issues cascade to other systems. Example: digestive dysfunction → nutrient malabsorption → liver stress → blood quality → nervous system effects.
2. KEY PATTERNS: Group related conditions and explain the biological mechanism connecting them, using the knowledge graph pathway data provided.
3. ACTIONABLE INSIGHTS: Based on the knowledge graph interventions and pathway data, suggest what areas to focus on first.

IMPORTANT RULES:
- Always frame findings as "patterns" and "associations", never as diagnoses
- Reference the actual scan scores and knowledge graph data
- Identify the ROOT SYSTEM — which organ system's dysfunction likely drives downstream effects
- Map the cascade: root → secondary → tertiary effects
- Be specific: name conditions, scores, and pathways
- End every section noting these are analytical patterns, not medical diagnoses

Return your analysis as valid JSON with this exact structure:
{
  "systemic_analysis": "2-3 paragraph narrative describing the overall pattern, root system identification, and cascade chain. Be specific with condition names and scores.",
  "root_systems": [
    {
      "organ_system": "name",
      "confidence": "high/medium/low",
      "reasoning": "why this appears to be a root driver",
      "downstream_effects": ["organ system 1", "organ system 2"]
    }
  ],
  "cascade_chains": [
    {
      "chain": ["organ1 → organ2 → organ3"],
      "mechanism": "explanation of the biological mechanism",
      "supporting_pathways": ["pathway names from KG data"],
      "key_conditions": ["condition names involved"]
    }
  ],
  "key_patterns": [
    {
      "pattern_name": "short descriptive name",
      "conditions_involved": ["condition1", "condition2"],
      "shared_pathways": ["pathway1"],
      "clinical_significance": "what this pattern suggests",
      "severity": "critical/high/moderate/low"
    }
  ],
  "actionable_insights": [
    {
      "priority": 1,
      "focus_area": "what to focus on",
      "reasoning": "why this should be addressed first",
      "supported_by": "knowledge graph evidence"
    }
  ]
}

Return ONLY the JSON. No markdown fences. No explanation outside the JSON."""

            prompt = f"""Analyze this MedBed scan data and knowledge graph context. Identify systemic cascade patterns, root organ systems, and actionable insights.

{context}

Produce your analysis as the JSON structure described in your instructions."""

            options = ClaudeAgentOptions(
                model=settings.ANTHROPIC_MODEL,
                system_prompt=system_prompt,
                allowed_tools=[],
                max_turns=1,
            )

            result_text = ""
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    break

            if not result_text or len(result_text) < 50:
                logger.warning("LLM clinical analysis returned empty result")
                return None

            # Parse JSON — handle potential markdown fences
            cleaned = result_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            logger.info(
                "LLM clinical analysis generated: %d root systems, %d cascades, %d patterns",
                len(parsed.get("root_systems", [])),
                len(parsed.get("cascade_chains", [])),
                len(parsed.get("key_patterns", [])),
            )
            return parsed

        except ImportError:
            logger.info("claude-agent-sdk not available; using template analysis")
            return None
        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON: %s", e)
            return None
        except Exception as e:
            logger.warning("LLM clinical analysis failed: %s", e)
            return None

    def _analyze_template(
        self,
        entries: list[dict],
        organ_risks: list[dict],
        systemic_patterns: list[dict] | None,
        graph_connectivity: dict | None,
    ) -> dict[str, Any]:
        """Template-based fallback when LLM is unavailable."""
        # Group conditions by organ system
        organ_groups: dict[str, list[dict]] = {}
        for e in entries:
            organ = e.get("organ_system", "Unknown")
            organ_groups.setdefault(organ, []).append(e)

        # Identify root systems (organs with most critical/high conditions)
        root_systems = []
        high_risk = [r for r in organ_risks if r["risk_tier"] in ("critical", "high")]
        for r in sorted(high_risk, key=lambda x: x.get("risk_score", 0)):
            downstream = []
            # Use shared pathways to find connected organs
            if systemic_patterns:
                connected_organs = set()
                organ_conditions = {
                    e.get("condition_name")
                    for e in organ_groups.get(r["organ_system"], [])
                }
                for sp in systemic_patterns:
                    if sp["disease1"] in organ_conditions:
                        # Find which organ system disease2 belongs to
                        for org, conds in organ_groups.items():
                            if any(c.get("condition_name") == sp["disease2"] for c in conds):
                                if org != r["organ_system"]:
                                    connected_organs.add(org)
                    elif sp["disease2"] in organ_conditions:
                        for org, conds in organ_groups.items():
                            if any(c.get("condition_name") == sp["disease1"] for c in conds):
                                if org != r["organ_system"]:
                                    connected_organs.add(org)
                downstream = list(connected_organs)[:3]

            root_systems.append({
                "organ_system": r["organ_system"],
                "confidence": "high" if r["risk_tier"] == "critical" else "medium",
                "reasoning": (
                    f"{r['condition_count']} conditions flagged with "
                    f"composite risk score {r.get('risk_score', 0):.3f}"
                ),
                "downstream_effects": downstream,
            })

        # Build cascade chains from pathway data
        cascade_chains = []
        if systemic_patterns and len(root_systems) > 0:
            root_organ = root_systems[0]["organ_system"]
            chain_organs = [root_organ] + root_systems[0].get("downstream_effects", [])
            if len(chain_organs) > 1:
                cascade_chains.append({
                    "chain": [" → ".join(chain_organs)],
                    "mechanism": "Shared biological pathways suggest systemic connection",
                    "supporting_pathways": list({
                        p for sp in systemic_patterns
                        for p in sp.get("pathway_names", [])
                    })[:5],
                    "key_conditions": list({
                        sp["disease1"] for sp in systemic_patterns[:5]
                    } | {
                        sp["disease2"] for sp in systemic_patterns[:5]
                    })[:8],
                })

        # Build key patterns
        key_patterns = []
        if systemic_patterns:
            pathway_groups: dict[str, list[str]] = {}
            for sp in systemic_patterns:
                for p in sp.get("pathway_names", []):
                    pathway_groups.setdefault(p, []).extend(
                        [sp["disease1"], sp["disease2"]]
                    )
            for pathway, conditions in sorted(
                pathway_groups.items(), key=lambda x: len(set(x[1])), reverse=True
            )[:5]:
                unique_conds = list(set(conditions))
                key_patterns.append({
                    "pattern_name": f"{pathway} cluster",
                    "conditions_involved": unique_conds[:5],
                    "shared_pathways": [pathway],
                    "clinical_significance": (
                        f"{len(unique_conds)} conditions share the {pathway} pathway, "
                        f"suggesting a common biological mechanism"
                    ),
                    "severity": "high" if len(unique_conds) > 3 else "moderate",
                })

        # Build narrative
        total = len(entries)
        narrative_parts = [
            f"Analysis of {total} conditions across {len(organ_risks)} organ systems "
            f"reveals {len(high_risk)} system(s) at elevated risk. "
        ]
        if root_systems:
            root = root_systems[0]
            narrative_parts.append(
                f"The {root['organ_system']} appears to be a primary driver "
                f"({root['reasoning']}). "
            )
            if root["downstream_effects"]:
                narrative_parts.append(
                    f"Shared biological pathways suggest downstream effects on "
                    f"{', '.join(root['downstream_effects'])}. "
                )
        narrative_parts.append(
            "These patterns are derived from frequency-based scan analysis and "
            "knowledge graph pathway data. They should be discussed with a "
            "qualified healthcare professional for proper clinical interpretation."
        )

        return {
            "systemic_analysis": "".join(narrative_parts),
            "root_systems": root_systems[:3],
            "cascade_chains": cascade_chains,
            "key_patterns": key_patterns[:5],
            "actionable_insights": [
                {
                    "priority": i + 1,
                    "focus_area": rs["organ_system"],
                    "reasoning": rs["reasoning"],
                    "supported_by": "Knowledge graph pathway analysis",
                }
                for i, rs in enumerate(root_systems[:3])
            ],
        }
