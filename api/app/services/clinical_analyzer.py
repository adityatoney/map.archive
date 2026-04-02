"""Agentic Clinical Analyzer — uses Claude (OAuth) to produce deep diagnostic insights.

Feeds the LLM the full knowledge graph context (shared pathways, comorbidities,
cascade patterns) along with scan data and asks for systemic pattern analysis,
root cause identification, and organ system cascade reasoning.

Uses Claude CLI (``claude -p``) in headless mode with OAuth authentication
(Claude Max subscription). The celery worker must run on the host (not Docker)
so the CLI can access the macOS Keychain for auth. No API key required.
No template fallback.
"""

import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------- System Prompt ----------

SYSTEM_PROMPT = """You are a clinical analytics engine for the MedBed Insight platform — a frequency-based bioresonance scan analyzer. You are NOT providing medical diagnosis or treatment. You are analyzing scan data patterns to help users understand potential systemic connections.

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


class ClinicalAnalyzerService:
    """Generate deep clinical insights using Claude LLM + knowledge graph context.

    Uses Anthropic SDK with OAuth (Claude Max subscription).
    No template fallback; always calls the LLM.
    """

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
          - _meta: dict — {source, model, input_tokens} for DB metadata
        """
        from app.models.recovery import MEDICAL_DISCLAIMER

        # Build the rich context for Claude
        context = self._build_analysis_context(
            entries, organ_risks, graph_interventions,
            systemic_patterns, graph_connectivity, trends,
            priority_conditions,
        )

        # Always use LLM via OAuth — no fallback
        result = await self._analyze_with_llm(context)
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
                    f"  {data.get('name', icd)}: pathways={data.get('pathway_count', 0)}, "
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

    async def _analyze_with_llm(self, context: str) -> dict[str, Any]:
        """Use Claude CLI (``claude -p``) to produce structured clinical insights.

        This is the ONLY analysis path — no template fallback.
        Raises on failure so the pipeline can handle it.

        Auth is handled by the Claude CLI natively (OAuth via Claude Max
        subscription, reading credentials from macOS Keychain).
        """
        from app.utils.claude_cli import claude_generate

        settings = get_settings()

        prompt = (
            "Analyze this MedBed scan data and knowledge graph context. "
            "Identify systemic cascade patterns, root organ systems, and "
            "actionable insights.\n\n"
            f"{context}\n\n"
            "Produce your analysis as the JSON structure described in your instructions."
        )

        response = await claude_generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=settings.ANTHROPIC_MODEL,
            max_turns=1,
            timeout=180,
        )

        result_text = response["result"]

        if not result_text or len(result_text) < 50:
            logger.error("Claude returned empty/short result (%d chars)", len(result_text))
            raise RuntimeError("Claude returned empty result")

        # Parse JSON — handle potential markdown fences
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (possibly with language tag)
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Claude returned invalid JSON: %s\nRaw: %s", e, cleaned[:500])
            raise RuntimeError(f"Claude returned invalid JSON: {e}") from e

        logger.info(
            "Clinical analysis generated: %d root systems, %d cascades, %d patterns",
            len(parsed.get("root_systems", [])),
            len(parsed.get("cascade_chains", [])),
            len(parsed.get("key_patterns", [])),
        )

        # Attach metadata
        parsed["_meta"] = {
            "source": "llm",
            "model": settings.ANTHROPIC_MODEL,
            "input_tokens": len(context) // 4,  # approximate
        }
        return parsed
