"""Report parser tests."""

import json

import pytest
from app.services.parser import parse_report


@pytest.mark.asyncio
async def test_parse_csv():
    """Parse a CSV report."""
    csv_content = b"""condition_name,score,anatomical_location,organ_system
ANAEMIA,0.188,BODY OF MAN,01 CORE PRODUCT
ATHEROSCLEROSIS,0.026,BODY OF MAN,01 CORE PRODUCT
CHRONIC REFLUX-GASTRITIS,0.433,CHOLESTERIN,02 DIGESTIVE SYSTEM
"""
    result = await parse_report(csv_content, "csv", "test.csv")
    entries = result["entries"]
    assert len(entries) == 3
    assert entries[0]["condition_name"] == "ANAEMIA"
    assert entries[0]["score"] == 0.188
    assert entries[2]["organ_system"] == "02 DIGESTIVE SYSTEM"


@pytest.mark.asyncio
async def test_parse_json_list():
    """Parse a JSON report (list format)."""
    data = [
        {
            "condition_name": "ANAEMIA",
            "score": 0.188,
            "anatomical_location": "BODY OF MAN",
            "organ_system": "01 CORE PRODUCT",
        },
        {
            "condition_name": "COLITIS",
            "score": 0.348,
            "anatomy": "WALL OF COLON",
        },
    ]
    result = await parse_report(json.dumps(data).encode(), "json", "test.json")
    entries = result["entries"]
    assert len(entries) == 2
    assert entries[1]["condition_name"] == "COLITIS"
    assert entries[1]["score"] == 0.348


@pytest.mark.asyncio
async def test_parse_json_dict():
    """Parse a JSON report (dict format with patient_info)."""
    data = {
        "patient_info": {"first_name": "Test", "last_name": "Patient"},
        "entries": [
            {"condition_name": "ANAEMIA", "score": 0.188},
        ],
    }
    result = await parse_report(json.dumps(data).encode(), "json", "test.json")
    assert result["patient_info"]["first_name"] == "Test"
    assert len(result["entries"]) == 1


@pytest.mark.asyncio
async def test_parse_unsupported_type():
    """Unsupported report type should raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported"):
        await parse_report(b"data", "xlsx", "test.xlsx")
