"""Temporal trend analyzer — tracks condition score changes across sessions.

Uses linear regression for trend direction and PELT algorithm (ruptures library)
for change-point detection of sudden score shifts.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Trend direction thresholds
STABLE_SLOPE_THRESHOLD = 0.015  # |slope| below this → stable
VOLATILE_STD_MULTIPLIER = 2.0  # std > this × |slope| + change points → volatile


class TrendAnalyzerService:
    """Analyze condition score trends across multiple scan sessions."""

    async def analyze_patient_trends(
        self,
        patient_id: str,
        sessions_data: list[dict],
        score_inverted: bool = True,
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

            score_values = [s["score"] for s in scores]
            first_score = score_values[0]
            last_score = score_values[-1]

            # Linear regression for slope
            x = np.arange(len(score_values))
            slope, _ = np.polyfit(x, score_values, 1)

            # PELT change-point detection
            change_points_detail = self._detect_change_points(scores)

            # Determine trend direction
            direction = self._classify_direction(
                slope, score_values, change_points_detail, score_inverted
            )

            trends.append(
                {
                    "condition_name": condition_name,
                    "condition_icd10": scores[-1].get("icd10"),
                    "organ_system": scores[-1].get("organ_system"),
                    "trend_direction": direction,
                    "trend_slope": round(float(slope), 4),
                    "sessions_analyzed": len(scores),
                    "first_score": first_score,
                    "last_score": last_score,
                    "change_points": change_points_detail,
                }
            )

        logger.info(
            "Trend analysis for patient %s: %d conditions tracked across %d sessions",
            patient_id,
            len(trends),
            len(sessions_data),
        )
        return trends

    def _detect_change_points(self, scores: list[dict]) -> list[dict]:
        """Detect sudden shifts in score trajectory using PELT algorithm.

        Requires at least 4 data points. Returns list of change-point dicts
        with session context.
        """
        if len(scores) < 4:
            return []

        try:
            import ruptures

            score_values = np.array([s["score"] for s in scores]).reshape(-1, 1)
            algo = ruptures.Pelt(model="rbf", min_size=2, jump=1)
            algo.fit(score_values)
            # pen=1.0 controls sensitivity; higher = fewer change points
            breakpoints = algo.predict(pen=1.0)

            # ruptures returns indices including the last index; remove it
            breakpoints = [bp for bp in breakpoints if bp < len(scores)]

            change_points_detail = []
            for bp_idx in breakpoints:
                if 0 < bp_idx < len(scores):
                    change_points_detail.append(
                        {
                            "session_index": bp_idx,
                            "session_id": scores[bp_idx].get("session_id"),
                            "scan_date": scores[bp_idx].get("scan_date"),
                            "score_before": scores[bp_idx - 1]["score"],
                            "score_after": scores[bp_idx]["score"],
                            "delta": round(
                                scores[bp_idx]["score"]
                                - scores[bp_idx - 1]["score"],
                                4,
                            ),
                        }
                    )
            return change_points_detail

        except ImportError:
            logger.warning(
                "ruptures library not available; skipping change-point detection"
            )
            return []
        except Exception as e:
            logger.warning("Change-point detection failed: %s", e)
            return []

    def _classify_direction(
        self,
        slope: float,
        score_values: list[float],
        change_points: list[dict],
        score_inverted: bool = True,
    ) -> str:
        """Classify trend direction from slope, variance, and change points.

        When score_inverted=True (MedBed default): lower score = worse,
        so rising slope (positive) = improving, falling slope = worsening.

        When score_inverted=False: higher score = worse,
        so falling slope (negative) = improving, rising slope = worsening.

        Returns: 'improving', 'worsening', 'stable', or 'volatile'
        """
        abs_slope = abs(slope)

        # Check for volatility: high variance relative to slope + change points
        if len(score_values) >= 4 and change_points:
            std = float(np.std(score_values))
            if std > VOLATILE_STD_MULTIPLIER * abs_slope and len(change_points) >= 2:
                return "volatile"

        # Standard direction classification
        if abs_slope < STABLE_SLOPE_THRESHOLD:
            return "stable"

        if score_inverted:
            # Inverted: rising score = getting healthier = improving
            return "improving" if slope > 0 else "worsening"
        else:
            # Normal: falling score = getting healthier = improving
            return "improving" if slope < 0 else "worsening"
