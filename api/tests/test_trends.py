"""Tests for temporal trend analysis and composite risk scoring.

Score interpretation: INVERTED (MedBed default)
  Lower score = higher risk (0-0.2 = high risk, 0.5+ = low risk)
  Rising score = improving (getting healthier)
  Falling score = worsening (getting sicker)
"""

import pytest

from app.services.trend_analyzer import TrendAnalyzerService
from app.services.risk_engine import RiskEngineService


@pytest.fixture
def trend_analyzer():
    return TrendAnalyzerService()


@pytest.fixture
def risk_engine():
    return RiskEngineService()


def _make_session(session_id, scan_date, entries):
    """Helper to build a session dict for trend analysis."""
    return {
        "session_id": session_id,
        "scan_date": scan_date,
        "entries": entries,
    }


def _make_entry(name, score, icd10="K29.40", organ="DIGESTIVE"):
    return {
        "condition_name": name,
        "score": score,
        "condition_icd10": icd10,
        "organ_system": organ,
    }


# --- Trend Analyzer Tests (inverted mode: lower = worse) ---


@pytest.mark.asyncio
async def test_trend_analyzer_single_session_returns_empty(trend_analyzer):
    """With only 1 session, no trends can be computed."""
    sessions = [
        _make_session("s1", "2026-01-01", [_make_entry("Gastritis", 0.3)])
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert trends == []


@pytest.mark.asyncio
async def test_trend_analyzer_improving_condition(trend_analyzer):
    """Score RISING across sessions should be 'improving' (inverted mode)."""
    sessions = [
        _make_session("s1", "2026-01-01", [_make_entry("Gastritis", 0.1)]),
        _make_session("s2", "2026-02-01", [_make_entry("Gastritis", 0.3)]),
        _make_session("s3", "2026-03-01", [_make_entry("Gastritis", 0.5)]),
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert len(trends) == 1
    assert trends[0]["trend_direction"] == "improving"
    assert trends[0]["trend_slope"] > 0  # Positive slope = score rising
    assert trends[0]["sessions_analyzed"] == 3
    assert trends[0]["first_score"] == 0.1
    assert trends[0]["last_score"] == 0.5


@pytest.mark.asyncio
async def test_trend_analyzer_worsening_condition(trend_analyzer):
    """Score FALLING across sessions should be 'worsening' (inverted mode)."""
    sessions = [
        _make_session("s1", "2026-01-01", [_make_entry("Bronchitis", 0.5)]),
        _make_session("s2", "2026-02-01", [_make_entry("Bronchitis", 0.3)]),
        _make_session("s3", "2026-03-01", [_make_entry("Bronchitis", 0.1)]),
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert len(trends) == 1
    assert trends[0]["trend_direction"] == "worsening"
    assert trends[0]["trend_slope"] < 0  # Negative slope = score falling


@pytest.mark.asyncio
async def test_trend_analyzer_stable_condition(trend_analyzer):
    """Small score changes should be classified as 'stable'."""
    sessions = [
        _make_session("s1", "2026-01-01", [_make_entry("Anaemia", 0.30)]),
        _make_session("s2", "2026-02-01", [_make_entry("Anaemia", 0.31)]),
        _make_session("s3", "2026-03-01", [_make_entry("Anaemia", 0.30)]),
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert len(trends) == 1
    assert trends[0]["trend_direction"] == "stable"


@pytest.mark.asyncio
async def test_trend_analyzer_multiple_conditions(trend_analyzer):
    """Multiple conditions should each get their own trend."""
    sessions = [
        _make_session(
            "s1",
            "2026-01-01",
            [
                _make_entry("Gastritis", 0.2),
                _make_entry("Anaemia", 0.4, icd10="D64.9"),
            ],
        ),
        _make_session(
            "s2",
            "2026-02-01",
            [
                _make_entry("Gastritis", 0.4),   # Rising = improving
                _make_entry("Anaemia", 0.2, icd10="D64.9"),  # Falling = worsening
            ],
        ),
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert len(trends) == 2

    trend_map = {t["condition_name"]: t for t in trends}
    assert trend_map["Gastritis"]["trend_direction"] == "improving"
    assert trend_map["Anaemia"]["trend_direction"] == "worsening"


@pytest.mark.asyncio
async def test_trend_analyzer_change_points(trend_analyzer):
    """PELT should detect sudden score shifts with >=4 data points."""
    sessions = [
        _make_session("s1", "2026-01-01", [_make_entry("Gastritis", 0.1)]),
        _make_session("s2", "2026-02-01", [_make_entry("Gastritis", 0.12)]),
        _make_session("s3", "2026-03-01", [_make_entry("Gastritis", 0.11)]),
        _make_session("s4", "2026-04-01", [_make_entry("Gastritis", 0.8)]),
        _make_session("s5", "2026-05-01", [_make_entry("Gastritis", 0.82)]),
    ]
    trends = await trend_analyzer.analyze_patient_trends(
        "p1", sessions, score_inverted=True
    )
    assert len(trends) == 1
    trend = trends[0]
    if trend["change_points"]:
        cp = trend["change_points"][0]
        assert "session_index" in cp
        assert "score_before" in cp
        assert "score_after" in cp
        assert "delta" in cp


# --- Composite Risk Scoring Tests (inverted: lower score = higher risk) ---


@pytest.mark.asyncio
async def test_composite_risk_with_no_extras(risk_engine):
    """Without trends/clusters/pathways, risk should be severity-only.

    With inverted mode, score 0.15 (high risk) gets severity = 1 - 0.15 = 0.85.
    Composite = 0.40 * 0.85 + 0.25 * 0.5 + 0.20 * 0.0 + 0.15 * 0.0 = 0.465
    """
    entries = [
        _make_entry("Gastritis", 0.15),
        _make_entry("Duodenitis", 0.35),
    ]
    results = await risk_engine.compute_organ_risk(entries)
    assert len(results) == 1
    assert results[0]["organ_system"] == "DIGESTIVE"
    assert "risk_components" in results[0]
    components = results[0]["risk_components"]
    assert components["trend"] == 0.5
    assert components["cluster_density"] == 0.0
    assert components["pathway_load"] == 0.0


@pytest.mark.asyncio
async def test_composite_risk_with_trends(risk_engine):
    """Worsening trends should increase risk score."""
    entries = [_make_entry("Gastritis", 0.3)]
    trends_worsening = [
        {
            "condition_name": "Gastritis",
            "organ_system": "DIGESTIVE",
            "trend_direction": "worsening",
        }
    ]
    trends_improving = [
        {
            "condition_name": "Gastritis",
            "organ_system": "DIGESTIVE",
            "trend_direction": "improving",
        }
    ]

    result_worsening = await risk_engine.compute_organ_risk(
        entries, trends=trends_worsening
    )
    result_improving = await risk_engine.compute_organ_risk(
        entries, trends=trends_improving
    )

    assert (
        result_worsening[0]["risk_score"] > result_improving[0]["risk_score"]
    )
    assert result_worsening[0]["risk_components"]["trend"] == 1.0
    assert result_improving[0]["risk_components"]["trend"] == 0.0


@pytest.mark.asyncio
async def test_composite_risk_with_pathway_counts(risk_engine):
    """Pathway load should increase risk score."""
    entries = [_make_entry("Gastritis", 0.3)]

    result_no_pathways = await risk_engine.compute_organ_risk(entries)
    result_with_pathways = await risk_engine.compute_organ_risk(
        entries, pathway_counts={"DIGESTIVE": 5}
    )

    assert (
        result_with_pathways[0]["risk_score"]
        > result_no_pathways[0]["risk_score"]
    )
    assert result_with_pathways[0]["risk_components"]["pathway_load"] == 1.0


@pytest.mark.asyncio
async def test_composite_risk_tier_assignment(risk_engine):
    """Verify risk tiers are assigned correctly with inverted scores.

    Inverted mode: low raw score = high severity.
    Score 0.05 → severity = 1 - (0.7*0.05 + 0.3*0.05) = 0.95
    With worsening trends: 0.40*0.95 + 0.25*1.0 = 0.63 → high/critical
    """
    # High score = low risk in inverted mode
    low_risk_entries = [_make_entry("Gastritis", 0.8)]
    low_result = await risk_engine.compute_organ_risk(low_risk_entries)
    assert low_result[0]["risk_tier"] == "low"

    # Low score + worsening trends = high/critical risk
    high_risk_entries = [_make_entry("Gastritis", 0.05)]
    worsening = [
        {
            "condition_name": "Gastritis",
            "organ_system": "DIGESTIVE",
            "trend_direction": "worsening",
        }
    ]
    high_result = await risk_engine.compute_organ_risk(
        high_risk_entries, trends=worsening
    )
    assert high_result[0]["risk_tier"] in ("high", "critical")
