"""Condition normalizer — maps condition names to ICD-10, SNOMED CT, and FMA codes.

In mock mode (UMLS_API_KEY=mock), uses a hardcoded lookup dictionary of common
Med Bed conditions. In production, calls the UMLS REST API with Redis caching
to avoid redundant lookups (UMLS results are deterministic).
"""

import hashlib
import json
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


# ---------------------------------------------------------------------------
# Redis cache helper
# ---------------------------------------------------------------------------

_CACHE_KEY_CONDITION = "umls:condition:{}"
_CACHE_KEY_ANATOMY = "umls:anatomy:{}"
# Sentinel value stored in Redis to represent a cached "no result" (avoids
# re-querying UMLS for anatomy locations that have no FMA mapping).
_CACHE_NULL = "__NULL__"


def _build_redis_url(base_url: str, db: int) -> str:
    """Swap the DB number in a redis:// URL.

    ``base_url`` is typically ``redis://redis:6379/0`` (Celery broker).
    We replace the trailing ``/0`` with ``/<db>`` for the cache DB.
    """
    # Strip trailing path component and replace with cache DB
    parts = base_url.rsplit("/", 1)
    return f"{parts[0]}/{db}"


class NormalizerService:
    """Maps condition names and anatomical locations to standard codes.

    When not in mock mode, results from the UMLS REST API are cached in
    Redis (DB 1 by default) with a configurable TTL (default 30 days).
    Cache failures are silently ignored — the service falls through to
    the UMLS API on any Redis error.
    """

    def __init__(self):
        settings = get_settings()
        self.mock_mode = settings.UMLS_API_KEY == "mock"
        self.umls_api_key = settings.UMLS_API_KEY
        self._cache_ttl = settings.UMLS_CACHE_TTL

        # Lazy-init Redis connection (only created when needed)
        self._redis = None
        self._redis_url = _build_redis_url(
            settings.REDIS_URL, settings.REDIS_CACHE_DB
        )

    async def _get_redis(self):
        """Return (and lazily create) the async Redis client."""
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
        return self._redis

    async def close(self):
        """Close the Redis connection pool (call after batch is done)."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    # ---- Cache helpers (never raise) ----

    async def _cache_get(self, key: str) -> str | None:
        """Get a value from Redis cache. Returns None on miss or error."""
        try:
            r = await self._get_redis()
            return await r.get(key)
        except Exception as e:
            logger.debug("Redis cache GET failed for %s: %s", key, e)
            return None

    async def _cache_set(self, key: str, value: str) -> None:
        """Set a value in Redis cache with TTL. Silently ignores errors."""
        try:
            r = await self._get_redis()
            await r.set(key, value, ex=self._cache_ttl)
        except Exception as e:
            logger.debug("Redis cache SET failed for %s: %s", key, e)

    # ---- Public API ----

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

    # ---- Mock (offline) implementations ----

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

    # ---- Real UMLS API implementations (with Redis caching) ----

    async def _umls_search(
        self,
        client: httpx.AsyncClient,
        string: str,
        sabs: str = "ICD10CM,SNOMEDCT_US",
        search_type: str = "exact",
    ) -> list[dict]:
        """Execute a single UMLS REST search and return the results list."""
        resp = await client.get(
            "https://uts-ws.nlm.nih.gov/rest/search/current",
            params={
                "string": string,
                "apiKey": self.umls_api_key,
                "sabs": sabs,
                "returnIdType": "code",
                "searchType": search_type,
            },
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("results", [])

    @staticmethod
    def _extract_codes(results: list[dict]) -> tuple[str | None, str | None]:
        """Extract the first ICD-10 and SNOMED code from UMLS results."""
        icd10 = None
        snomed = None
        for r in results:
            root_source = r.get("rootSource", "")
            if root_source == "ICD10CM" and not icd10:
                icd10 = r.get("ui")
            elif root_source == "SNOMEDCT_US" and not snomed:
                snomed = r.get("ui")
        return icd10, snomed

    async def _real_normalize_condition(self, condition_name: str) -> dict:
        """Call the UMLS REST API for real normalization.

        Uses a multi-pass strategy to maximize ICD-10 hit rate:
          1. Exact match against ICD10CM + SNOMEDCT_US
          2. If ICD-10 still missing → "words" (fuzzy) search against ICD10CM only
          3. If still missing → fall back to the hardcoded mock dictionary
             (which contains curated mappings for common Med Bed conditions)

        Results are cached in Redis. Mock-only fallback results from API
        *errors* are NOT cached so the real API is retried next time.
        """
        name_upper = condition_name.upper().strip()
        cache_key = _CACHE_KEY_CONDITION.format(name_upper)

        # --- Check cache ---
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("UMLS cache HIT (condition): %s", name_upper)
            return json.loads(cached)

        # --- Cache miss: call UMLS ---
        logger.debug("UMLS cache MISS (condition): %s", name_upper)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Pass 1: exact match across both vocabularies
                results = await self._umls_search(
                    client, condition_name, sabs="ICD10CM,SNOMEDCT_US", search_type="exact"
                )
                icd10, snomed = self._extract_codes(results)

                # Pass 2: if ICD-10 missing, try a broader "words" search
                # against ICD-10-CM only (handles spelling variants, partial matches)
                if not icd10:
                    results2 = await self._umls_search(
                        client, condition_name, sabs="ICD10CM", search_type="words"
                    )
                    icd10_2, _ = self._extract_codes(results2)
                    if icd10_2:
                        icd10 = icd10_2

                # Pass 3: if still no ICD-10, check the curated mock dictionary
                # (contains known-good mappings for Med Bed-specific terminology)
                if not icd10:
                    mock_icd10 = MOCK_ICD10_MAP.get(name_upper)
                    if mock_icd10:
                        icd10 = mock_icd10
                        logger.debug(
                            "ICD-10 from curated dictionary: %s → %s",
                            name_upper, icd10,
                        )

                if not snomed:
                    mock_snomed = MOCK_SNOMED_MAP.get(name_upper)
                    if mock_snomed:
                        snomed = mock_snomed

                result = {"icd10": icd10, "snomed": snomed}

                # Cache the API + dictionary merged result
                await self._cache_set(cache_key, json.dumps(result))
                return result

        except Exception as e:
            logger.warning(
                "UMLS API call failed for '%s': %s. Using mock.", condition_name, e
            )
            # Do NOT cache mock fallback — we want to retry UMLS next time
            return self._mock_normalize_condition(condition_name)

    async def _real_normalize_anatomy(self, location: str) -> str | None:
        """Call UMLS for FMA mapping with Redis caching.

        Caches both positive results (FMA IDs) and negative results (no mapping)
        to avoid re-querying UMLS for locations that have no FMA entry.
        Mock fallback results are NOT cached.
        """
        loc_upper = location.upper().strip()
        cache_key = _CACHE_KEY_ANATOMY.format(loc_upper)

        # --- Check cache ---
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("UMLS cache HIT (anatomy): %s", loc_upper)
            return None if cached == _CACHE_NULL else cached

        # --- Cache miss: call UMLS ---
        logger.debug("UMLS cache MISS (anatomy): %s", loc_upper)
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
                    fma_id = f"FMA:{results[0].get('ui', '')}"
                    await self._cache_set(cache_key, fma_id)
                    return fma_id

                # No FMA result — cache the "null" sentinel
                await self._cache_set(cache_key, _CACHE_NULL)
                return None

        except Exception as e:
            logger.warning(
                "UMLS FMA lookup failed for '%s': %s. Using mock.", location, e
            )
            # Do NOT cache mock fallback
            return self._mock_normalize_anatomy(location)
