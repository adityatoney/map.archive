"""UMLS-powered SNOMED CT enrichment script.

One-time script to query UMLS REST API for SNOMED codes for all conditions
in the normalizer's MOCK_ICD10_MAP, expanding coverage from 17 to ~89 conditions.

When a condition's original (often archaic/Eastern European) name has no exact
SNOMED match, a synonym map provides the modern English equivalent for re-query.
The SNOMED code is stored against the *original* condition name.

Usage:
    python -m app.enrich_snomed [--dry-run]
"""

import argparse
import logging
import sys
import time

import httpx

from app.config import get_settings
from app.services.normalizer import MOCK_ICD10_MAP, MOCK_SNOMED_MAP

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

UMLS_SEARCH_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"

# Synonym map: archaic/regional term → modern SNOMED-friendly equivalent.
# Used as a fallback when the original term yields no UMLS result.
SYNONYM_MAP: dict[str, str] = {
    "CALCULARY CHOLECYSTITIS": "Calculous cholecystitis",
    "CATARRHAL GASTRITIS": "Acute gastritis",
    "CHRONIC BRONCHIAL CATARRH": "Chronic bronchitis",
    "COMMISSURAL DISEASE": "Peritoneal adhesions",
    "DYSKINESIA OF GALLBLADDER": "Biliary dyskinesia",
    "MULTIPLE BRONCHIECTASIS": "Bronchiectasis",
    "MYOCARDIODYSTROPHY": "Cardiomyopathy",
    "NEPHROPTOSIS": "Floating kidney",
    "NEURASTHENIA": "Chronic fatigue syndrome",
    "PAPILLARY CANCER OF THE LARYNX": "Papillary carcinoma of larynx",
    "SCAPULOHUMERAL PERIARTHRITIS": "Adhesive capsulitis of shoulder",
    "SPONDYLARTHROSIS DEFORMANS": "Spondylosis",
    "TROPHIC CRUS ULCERS": "Trophic ulcer of lower limb",
    "VARIX DILATATION": "Varicose veins",
    "VEGETATIVE-VASCULAR DYSTONIA": "Autonomic dysfunction",
    "CHOLESTATIC HEPATOSIS": "Cholestasis",
    "CHRONIC AUTOIMMUNE GASTRITIS": "Autoimmune gastritis",
    "CHRONIC REFLUX-GASTRITIS": "Bile reflux gastritis",
    "CHRONIC RELAPSING PANCREATITIS": "Chronic pancreatitis",
    "CHRONIC NONCOMPLICATED GASTRIC ULCER": "Chronic gastric ulcer",
    "FIBROMA OF THE STOMACH": "Benign neoplasm of stomach",
    "EPIDERMOID CARCINOMA OF THE PANCREAS": "Squamous cell carcinoma of pancreas",
    "HEPATOCEREBRAL DYSTROPHY": "Hepatolenticular degeneration",
    "PERIPORTAL HEPATIC FIBROSIS": "Hepatic fibrosis",
    "INTESTINAL DISBACTERIOSIS": "Intestinal dysbiosis",
}


def query_umls_snomed(condition_name: str, api_key: str) -> str | None:
    """Query UMLS REST API for a SNOMED CT code for a condition name."""
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                UMLS_SEARCH_URL,
                params={
                    "string": condition_name,
                    "apiKey": api_key,
                    "sabs": "SNOMEDCT_US",
                    "returnIdType": "code",
                    "pageSize": 5,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("result", {}).get("results", [])

            for r in results:
                if r.get("rootSource") == "SNOMEDCT_US":
                    return r.get("ui")

        return None
    except Exception as e:
        logger.warning("  UMLS query failed for '%s': %s", condition_name, e)
        return None


def run_enrichment(dry_run: bool = False):
    """Run SNOMED enrichment for all conditions in MOCK_ICD10_MAP."""
    settings = get_settings()

    if settings.UMLS_API_KEY == "mock":
        logger.error(
            "UMLS_API_KEY is set to 'mock'. Set a real API key to run enrichment."
        )
        sys.exit(1)

    api_key = settings.UMLS_API_KEY

    # Find conditions missing SNOMED codes
    conditions = list(MOCK_ICD10_MAP.keys())
    existing_snomed = set(MOCK_SNOMED_MAP.keys())
    missing = [c for c in conditions if c not in existing_snomed]

    logger.info("=== SNOMED CT Enrichment via UMLS API ===")
    logger.info("Total conditions in ICD-10 map: %d", len(conditions))
    logger.info("Already have SNOMED codes: %d", len(existing_snomed))
    logger.info("Missing SNOMED codes: %d", len(missing))
    logger.info("")

    if not missing:
        logger.info("All conditions already have SNOMED codes. Nothing to do.")
        return

    new_mappings: dict[str, str] = {}
    failed: list[str] = []

    for i, condition_name in enumerate(missing):
        logger.info(
            "[%d/%d] Querying SNOMED for: %s",
            i + 1,
            len(missing),
            condition_name,
        )

        snomed_code = query_umls_snomed(condition_name, api_key)

        if snomed_code:
            new_mappings[condition_name] = snomed_code
            logger.info("  → Found: %s", snomed_code)
        elif condition_name in SYNONYM_MAP:
            # Retry with modern synonym
            synonym = SYNONYM_MAP[condition_name]
            logger.info("  → Not found, retrying with synonym: %s", synonym)
            time.sleep(0.1)
            snomed_code = query_umls_snomed(synonym, api_key)
            if snomed_code:
                new_mappings[condition_name] = snomed_code
                logger.info("  → Found via synonym: %s", snomed_code)
            else:
                failed.append(condition_name)
                logger.info("  → Not found (even with synonym)")
        else:
            failed.append(condition_name)
            logger.info("  → Not found")

        # Rate limiting: UMLS allows 20 requests/second
        time.sleep(0.1)

    # Report results
    logger.info("")
    logger.info("=== Results ===")
    logger.info("New SNOMED codes found: %d", len(new_mappings))
    logger.info("Not found: %d", len(failed))

    if new_mappings:
        logger.info("")
        logger.info("=== New MOCK_SNOMED_MAP entries ===")
        logger.info("Add these to api/app/services/normalizer.py:\n")
        for name, code in sorted(new_mappings.items()):
            logger.info('    "%s": "%s",', name, code)

    if dry_run:
        logger.info("\n[DRY RUN] No files were modified.")
        return

    # Auto-update normalizer.py if not dry run
    if new_mappings:
        _update_normalizer_file(new_mappings)
        logger.info(
            "\nUpdated normalizer.py with %d new SNOMED mappings.",
            len(new_mappings),
        )


def _update_normalizer_file(new_mappings: dict[str, str]):
    """Append new SNOMED mappings to MOCK_SNOMED_MAP in normalizer.py."""
    import re

    filepath = "app/services/normalizer.py"
    with open(filepath) as f:
        content = f.read()

    # Find the closing brace of MOCK_SNOMED_MAP
    # Pattern: find the last entry before the closing }
    pattern = r"(MOCK_SNOMED_MAP: dict\[str, str\] = \{[^}]*)(})"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        logger.error("Could not find MOCK_SNOMED_MAP in %s", filepath)
        return

    # Build new entries
    new_entries = "\n".join(
        f'    "{name}": "{code}",'
        for name, code in sorted(new_mappings.items())
    )

    # Insert before closing brace
    updated = content[: match.end(1)] + "\n" + new_entries + "\n" + content[match.start(2):]

    with open(filepath, "w") as f:
        f.write(updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich SNOMED CT codes via UMLS API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query UMLS but don't modify files",
    )
    args = parser.parse_args()
    run_enrichment(dry_run=args.dry_run)
