"""Condition normalizer — maps condition names to ICD-10, SNOMED CT, and FMA codes.

In mock mode (UMLS_API_KEY=mock), uses a hardcoded lookup dictionary of common
Med Bed conditions. In production, calls the UMLS REST API.
"""

import hashlib
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Hardcoded mappings for common Tesla Med Bed conditions
MOCK_ICD10_MAP: dict[str, str] = {
    "ANAEMIA": "D64.9",
    "ATHEROSCLEROSIS": "I70.9",
    "ATROPHIC GASTRITIS": "K29.40",
    "ATROPHIC HYPERPLASTIC GASTRITIS": "K29.40",
    "BAASTRUP'S DISEASE": "M48.27",
    "BRONCHIAL ASTHMA": "J45.9",
    "BRONCHOGENIC CARCINOMA": "C34.9",
    "CALCULARY CHOLECYSTITIS": "K80.10",
    "CALF MUSCLE SPASM": "R25.2",
    "CARDIAC ARRHYTHMIA": "I49.9",
    "CATARRHAL GASTRITIS": "K29.00",
    "CHOLELITHIASIS": "K80.20",
    "CHRONIC BRONCHIAL CATARRH": "J42",
    "CHRONIC RELAPSING HEPATITIS": "K73.9",
    "COMMISSURAL DISEASE": "K66.0",
    "DEFLECTED NASAL SEPTUM": "J34.2",
    "DIFFUSE GOITER": "E04.0",
    "DUODENITIS": "K29.80",
    "DYSKINESIA OF GALLBLADDER": "K82.8",
    "ENTERITIS": "K52.9",
    "FARSIGHTEDNESS": "H52.0",
    "GASTROPTOSIS": "K31.89",
    "HAEMORRHOIDS": "K64.9",
    "HELMINTHIASIS": "B83.9",
    "HYPERTROPHIC GASTRITIS": "K29.60",
    "HYPOTENSION": "I95.9",
    "HYPOTHYROIDISM": "E03.9",
    "IDIOPATHIC HYPERTENSION": "I10",
    "INSULIN-DEPENDENT DIABETES MELLITUS": "E10.9",
    "MULTIPLE BRONCHIECTASIS": "J47.9",
    "MYOCARDIODYSTROPHY": "I42.9",
    "NEPHROPTOSIS": "N28.89",
    "NEURALGIA": "M79.2",
    "NEURASTHENIA": "F48.0",
    "ORCHITIS": "N45.9",
    "OSTEOARTHRITIS DEFORMANS": "M19.90",
    "OSTEOPOROSIS": "M81.0",
    "PAPILLARY CANCER OF THE LARYNX": "C32.0",
    "POLLINOSIS": "J30.1",
    "POLYARTHRITIS": "M13.0",
    "PROSTATITIS": "N41.9",
    "RADICULOPATHY": "M54.10",
    "RENAL HYDRONEPHROSIS": "N13.30",
    "RHEUMATIC CARDITIS": "I09.9",
    "SCAPULOHUMERAL PERIARTHRITIS": "M75.00",
    "SPONDYLARTHROSIS DEFORMANS": "M47.819",
    "THROMBOPHLEBITIS": "I80.9",
    "TROPHIC CRUS ULCERS": "L97.909",
    "VARIX DILATATION": "I83.90",
    "VEGETATIVE-VASCULAR DYSTONIA": "G90.9",
    "CHOLESTATIC HEPATOSIS": "K71.0",
    "CHRONIC AUTOIMMUNE GASTRITIS": "K29.40",
    "CHRONIC REFLUX-GASTRITIS": "K21.0",
    "CHRONIC RELAPSING PANCREATITIS": "K86.1",
    "CHRONIC TONSILLITIS": "J35.0",
    "COLITIS": "K52.9",
    "DUODENAL ULCER": "K26.9",
    "EPIDERMOID CARCINOMA OF THE PANCREAS": "C25.9",
    "FATTY HEPATOSIS": "K76.0",
    "GASTRITIS": "K29.70",
    "GLUTEN ENTEROPATHY": "K90.0",
    "HEPATOCEREBRAL DYSTROPHY": "E83.01",
    "PORPHYRIA": "E80.20",
    "PRIMARY BILIARY CIRRHOSIS": "K74.3",
    "CHRONIC NONCOMPLICATED GASTRIC ULCER": "K25.7",
    "FIBROMA OF THE STOMACH": "D13.1",
    "LARYNGITIS": "J04.0",
    "PHARYNGITIS": "J02.9",
    "PERIPORTAL HEPATIC FIBROSIS": "K74.0",
    "PANCREAS ADENOCARCINOMA": "C25.9",
    "INTESTINAL DISBACTERIOSIS": "K63.8",
}

MOCK_SNOMED_MAP: dict[str, str] = {
    "ANAEMIA": "271737000",
    "ATHEROSCLEROSIS": "38716007",
    "ATROPHIC GASTRITIS": "4998003",
    "BRONCHIAL ASTHMA": "195967001",
    "CARDIAC ARRHYTHMIA": "698247007",
    "CHOLELITHIASIS": "235919008",
    "CHRONIC RELAPSING HEPATITIS": "76783007",
    "DUODENITIS": "51868009",
    "HAEMORRHOIDS": "70153002",
    "HELMINTHIASIS": "27601005",
    "HYPOTHYROIDISM": "40930008",
    "IDIOPATHIC HYPERTENSION": "59621000",
    "OSTEOPOROSIS": "64859006",
    "PROSTATITIS": "9713002",
    "COLITIS": "64226004",
    "FATTY HEPATOSIS": "197321007",
    "GASTRITIS": "4556007",

    "ATROPHIC HYPERPLASTIC GASTRITIS": "3308008",
    "BAASTRUP'S DISEASE": "312381000119103",
    "BRONCHOGENIC CARCINOMA": "254622008",
    "CALF MUSCLE SPASM": "15748441000119106",
    "CHRONIC TONSILLITIS": "90979004",
    "DEFLECTED NASAL SEPTUM": "74808006",
    "DIFFUSE GOITER": "267374005",
    "DUODENAL ULCER": "51868009",
    "ENTERITIS": "64613007",
    "FARSIGHTEDNESS": "38101003",
    "GASTROPTOSIS": "1208004",
    "GLUTEN ENTEROPATHY": "396331005",
    "HYPERTROPHIC GASTRITIS": "60002000",
    "HYPOTENSION": "45007003",
    "INSULIN-DEPENDENT DIABETES MELLITUS": "23045005",
    "LARYNGITIS": "45913009",
    "NEURALGIA": "31681005",
    "ORCHITIS": "274718005",
    "OSTEOARTHRITIS DEFORMANS": "396275006",
    "PANCREAS ADENOCARCINOMA": "700423003",
    "PHARYNGITIS": "405737000",
    "POLLINOSIS": "21719001",
    "POLYARTHRITIS": "416956002",
    "PORPHYRIA": "418470004",
    "PRIMARY BILIARY CIRRHOSIS": "31712002",
    "RADICULOPATHY": "72274001",
    "RENAL HYDRONEPHROSIS": "736640009",
    "RHEUMATIC CARDITIS": "1148763004",
    "THROMBOPHLEBITIS": "64156001",

    "CALCULARY CHOLECYSTITIS": "1269314004",
    "CATARRHAL GASTRITIS": "25458004",
    "CHOLESTATIC HEPATOSIS": "33688009",
    "CHRONIC AUTOIMMUNE GASTRITIS": "84568007",
    "CHRONIC BRONCHIAL CATARRH": "63480004",
    "CHRONIC NONCOMPLICATED GASTRIC ULCER": "76796008",
    "CHRONIC REFLUX-GASTRITIS": "72950008",
    "CHRONIC RELAPSING PANCREATITIS": "235494005",
    "COMMISSURAL DISEASE": "70190001",
    "DYSKINESIA OF GALLBLADDER": "197432008",
    "EPIDERMOID CARCINOMA OF THE PANCREAS": "770602005",
    "FIBROMA OF THE STOMACH": "92411005",
    "HEPATOCEREBRAL DYSTROPHY": "88518009",
    "INTESTINAL DISBACTERIOSIS": "1149492007",
    "MULTIPLE BRONCHIECTASIS": "12295008",
    "MYOCARDIODYSTROPHY": "85898001",
    "NEPHROPTOSIS": "9918001",
    "NEURASTHENIA": "52702003",
    "PAPILLARY CANCER OF THE LARYNX": "1260073003",
    "PERIPORTAL HEPATIC FIBROSIS": "62484002",
    "SCAPULOHUMERAL PERIARTHRITIS": "399114005",
    "SPONDYLARTHROSIS DEFORMANS": "8847002",
    "TROPHIC CRUS ULCERS": "36347008",
    "VARIX DILATATION": "128060009",
    "VEGETATIVE-VASCULAR DYSTONIA": "231517009",
}

MOCK_FMA_MAP: dict[str, str] = {
    "BODY OF MAN": "FMA:20394",
    "CROSS SECTION THROUGH ABDOMEN AT THE LEVEL OF 2ND LUMBAR VERTEBRA": "FMA:14600",
    "PARASAGITTAL INCISION OF THE BODY,ON THE LEVEL OF THE LEFT KIDNEY": "FMA:7203",
    "CROSS - SECTION OF NECK": "FMA:7155",
    "HEAD FRONTAL CROSS-SECTION": "FMA:46565",
    "TRANSITION OF ESOPHAGUS TO STOMACH": "FMA:9434",
    "AMPULLA OF VATER DUCT": "FMA:15076",
    "INTERLOBULAR BILE DUCT": "FMA:17536",
    "HEPATIC BEAM TISSUE": "FMA:68646",
    "CHOLESTERIN": "FMA:12277",
    "PANCREATIC DUCT WALL": "FMA:16003",
    "GULLET CUT": "FMA:7131",
    "WALL OF COLON": "FMA:14541",
    "COLON WALL": "FMA:14541",
    "WALL OF DOUDENUM": "FMA:14928",
    "WALL OF GALL BLADDER": "FMA:14658",
    "WALL OF SMALL INTESTINE": "FMA:14931",
    "PANCREATIC ACINUS": "FMA:16004",
    "HEPATOCYTE": "FMA:14515",
    "STOMACH GLANDS": "FMA:14920",
    "INTESTINE EPITHELIAL CELL": "FMA:62122",
    "WALL OF RECTUM": "FMA:15388",
    "INTESTINE WALL (SMALL INTESTINE)": "FMA:14931",
    "SUPERFICIAL MUCOUS GLANDS OF STOMACH WALL": "FMA:14920",
    "ACINIC INSULAR CELLS OF PANCREAS": "FMA:16013",
    "DUODENUM AND PANCREAS ARTERIES": "FMA:14803",
    "NERVES OF STOMACH": "FMA:14640",
    "ESOPHAGUS, STOMACH, DUODENUM, FRONT VIEW": "FMA:9434",
    "SKIN TISSUE": "FMA:7163",
    "HAIR TISSUE": "FMA:70752",
    "SPLEEN TISSUE": "FMA:7196",
    "LYMPHATIC VESSEL": "FMA:30315",
    "NEURO - VESSEL FASCICLE": "FMA:65239",
    "CEREBELLUM TISSUE": "FMA:67944",
    "WALL OF HEART": "FMA:9550",
    "BRONCHUS TRANSVERSAL SECTION": "FMA:7409",
    "PROSTATE": "FMA:9600",
    "SET OF MALE CHROMOSOMES.": "FMA:67099",
    "HISTAMINE": "FMA:0",
    "TONSIL TISSUE": "FMA:9609",
    "MALE URINARY BLADDER; REAR VIEW": "FMA:15900",
    "ARTERIOLA": "FMA:63183",
    "BASOPHILIC LEUKOCYTE": "FMA:62861",
    "MUCOUS GLAND": "FMA:71645",
    "PARANASAL SINUSES; LEFT VIEW": "FMA:59679",
    "PARANASAL SINUSES; RIGHT VIEW": "FMA:59679",
}


class NormalizerService:
    """Maps condition names and anatomical locations to standard codes."""

    def __init__(self):
        settings = get_settings()
        self.mock_mode = settings.UMLS_API_KEY == "mock"
        self.umls_api_key = settings.UMLS_API_KEY

    async def normalize_condition(self, condition_name: str) -> dict:
        """Map a condition name to ICD-10 and SNOMED codes.

        Returns:
            {"icd10": str | None, "snomed": str | None}
        """
        if self.mock_mode:
            return self._mock_normalize_condition(condition_name)
        return await self._real_normalize_condition(condition_name)

    async def normalize_anatomy(self, location: str) -> str | None:
        """Map an anatomical location string to an FMA identifier.

        Returns:
            FMA ID string or None
        """
        if self.mock_mode:
            return self._mock_normalize_anatomy(location)
        return await self._real_normalize_anatomy(location)

    def _mock_normalize_condition(self, condition_name: str) -> dict:
        """Use hardcoded lookup dictionary."""
        name_upper = condition_name.upper().strip()
        icd10 = MOCK_ICD10_MAP.get(name_upper)
        snomed = MOCK_SNOMED_MAP.get(name_upper)

        if not icd10:
            # Generate a deterministic placeholder for unmapped conditions
            hash_val = hashlib.md5(name_upper.encode()).hexdigest()[:4].upper()
            icd10 = f"U{hash_val[:3]}.{hash_val[3]}"

        return {"icd10": icd10, "snomed": snomed}

    def _mock_normalize_anatomy(self, location: str) -> str | None:
        """Use hardcoded FMA lookup."""
        loc_upper = location.upper().strip()
        return MOCK_FMA_MAP.get(loc_upper)

    async def _real_normalize_condition(self, condition_name: str) -> dict:
        """Call the UMLS REST API for real normalization."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search UMLS for the condition
                resp = await client.get(
                    "https://uts-ws.nlm.nih.gov/rest/search/current",
                    params={
                        "string": condition_name,
                        "apiKey": self.umls_api_key,
                        "sabs": "ICD10CM,SNOMEDCT_US",
                        "returnIdType": "code",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("result", {}).get("results", [])

                icd10 = None
                snomed = None
                for r in results:
                    root_source = r.get("rootSource", "")
                    if root_source == "ICD10CM" and not icd10:
                        icd10 = r.get("ui")
                    elif root_source == "SNOMEDCT_US" and not snomed:
                        snomed = r.get("ui")

                return {"icd10": icd10, "snomed": snomed}
        except Exception as e:
            logger.warning("UMLS API call failed for '%s': %s. Using mock.", condition_name, e)
            return self._mock_normalize_condition(condition_name)

    async def _real_normalize_anatomy(self, location: str) -> str | None:
        """Call UMLS for FMA mapping. Falls back to mock on failure."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://uts-ws.nlm.nih.gov/rest/search/current",
                    params={
                        "string": location,
                        "apiKey": self.umls_api_key,
                        "sabs": "FMA",
                        "returnIdType": "code",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("result", {}).get("results", [])
                if results:
                    return f"FMA:{results[0].get('ui', '')}"
                return None
        except Exception as e:
            logger.warning("UMLS FMA lookup failed for '%s': %s. Using mock.", location, e)
            return self._mock_normalize_anatomy(location)
