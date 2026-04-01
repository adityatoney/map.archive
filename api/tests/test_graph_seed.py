"""Tests for knowledge graph seed data completeness.

Ensures every ICD-10 code from the normalizer has a corresponding
disease record in the biomedical knowledge base, and all cross-references
are valid.
"""

from app.data.biomedical_knowledge import (
    DISEASES,
    LIFESTYLE_INTERVENTIONS,
    NUTRITIONAL_FACTORS,
    PATHWAYS,
)
from app.services.normalizer import MOCK_ICD10_MAP


def test_all_normalizer_icds_have_disease_records():
    """Every ICD-10 code in MOCK_ICD10_MAP must exist in DISEASES."""
    normalizer_icds = set(MOCK_ICD10_MAP.values())
    knowledge_icds = set(DISEASES.keys())
    missing = normalizer_icds - knowledge_icds
    assert not missing, (
        f"ICD-10 codes in normalizer but not in knowledge graph: {missing}"
    )


def test_all_diseases_have_required_fields():
    """Every disease record must have at least 1 pathway and 1 nutritional factor."""
    for icd, disease in DISEASES.items():
        assert len(disease["pathways"]) >= 1, f"{icd} ({disease['name']}) has no pathways"
        assert len(disease["nutritional_factors"]) >= 1, (
            f"{icd} ({disease['name']}) has no nutritional factors"
        )
        assert len(disease["lifestyle_interventions"]) >= 1, (
            f"{icd} ({disease['name']}) has no lifestyle interventions"
        )
        assert disease["name"], f"{icd} has no name"


def test_pathway_references_are_valid():
    """Disease pathway references must exist in PATHWAYS dict."""
    all_pathway_names = set(PATHWAYS.keys())
    for icd, disease in DISEASES.items():
        for pathway in disease["pathways"]:
            assert pathway in all_pathway_names, (
                f"{icd} ({disease['name']}) references unknown pathway: '{pathway}'"
            )


def test_nutritional_factor_references_are_valid():
    """Disease nutritional factor references must exist in NUTRITIONAL_FACTORS dict."""
    all_nf_names = set(NUTRITIONAL_FACTORS.keys())
    for icd, disease in DISEASES.items():
        for nf in disease["nutritional_factors"]:
            assert nf in all_nf_names, (
                f"{icd} ({disease['name']}) references unknown nutritional factor: '{nf}'"
            )


def test_lifestyle_references_are_valid():
    """Disease lifestyle intervention references must exist in LIFESTYLE_INTERVENTIONS dict."""
    all_li_names = set(LIFESTYLE_INTERVENTIONS.keys())
    for icd, disease in DISEASES.items():
        for li in disease["lifestyle_interventions"]:
            assert li in all_li_names, (
                f"{icd} ({disease['name']}) references unknown lifestyle intervention: '{li}'"
            )


def test_comorbidity_references_are_valid():
    """comorbid_with ICD-10 codes must exist as Disease entries."""
    for icd, disease in DISEASES.items():
        for other in disease.get("comorbid_with", []):
            assert other in DISEASES, (
                f"{icd} ({disease['name']}) comorbid_with unknown ICD: '{other}'"
            )


def test_disease_count_is_sufficient():
    """We should have at least 50 diseases (matching normalizer coverage)."""
    assert len(DISEASES) >= 50, (
        f"Expected at least 50 diseases, got {len(DISEASES)}"
    )


def test_pathway_count_is_sufficient():
    """We should have a reasonable number of pathways."""
    assert len(PATHWAYS) >= 20, (
        f"Expected at least 20 pathways, got {len(PATHWAYS)}"
    )


def test_shared_pathways_exist():
    """At least some disease pairs should share pathways (for find_shared_pathways)."""
    pathway_to_diseases: dict[str, list[str]] = {}
    for icd, disease in DISEASES.items():
        for pathway in disease["pathways"]:
            pathway_to_diseases.setdefault(pathway, []).append(icd)

    shared_pathways = {
        p: diseases
        for p, diseases in pathway_to_diseases.items()
        if len(diseases) >= 2
    }
    assert len(shared_pathways) >= 10, (
        f"Expected at least 10 pathways shared by 2+ diseases, got {len(shared_pathways)}"
    )
