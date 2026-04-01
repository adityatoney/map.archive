# Phase 3: Knowledge Graph Seeding & Pipeline Integration

## Context

Phases 1-2 are complete: the NLP pipeline works end-to-end (PDF → parse → normalize → embed → cluster → risk → recovery plan). Neo4j 5 is running in Docker with APOC plugin but is **completely empty**. `graph_client.py` has 5 query methods that gracefully return `[]` when there's no data. The recovery planner has an unused `graph_interventions` parameter, and the insights router returns empty `shared_pathways` and `patterns`.

**Goal**: Populate Neo4j with curated biomedical knowledge for the 56+ conditions in our normalizer's ICD-10 map, then wire the graph into the analysis pipeline so recovery plans and insights are evidence-based instead of template-based.

---

## Wave 1: Curated Biomedical Knowledge Data Module

### 1a. Create data package
**New file**: `api/app/data/__init__.py` — empty init

### 1b. Create curated knowledge base
**New file**: `api/app/data/biomedical_knowledge.py`

A single Python module containing all seed data as typed dictionaries. Every ICD-10 code in `normalizer.py`'s `MOCK_ICD10_MAP` gets a complete entry.

**Data structures**:
```python
PATHWAYS: dict[str, dict]  # ~40 entries
# {"Inflammatory response": {"kegg_id": "hsa04668", "category": "immune"}, ...}

NUTRITIONAL_FACTORS: dict[str, dict]  # ~30 entries
# {"Vitamin D": {"type": "vitamin", "evidence_level": "strong"}, ...}

LIFESTYLE_INTERVENTIONS: dict[str, dict]  # ~25 entries
# {"Aerobic exercise": {"category": "exercise", "evidence_level": "strong"}, ...}

DISEASES: dict[str, DiseaseRecord]  # 56+ entries, keyed by ICD-10
# Each entry has: name, pathways[], nutritional_factors[], lifestyle_interventions[],
#   anatomical_structures[], genes[], phenotypes[], comorbid_with[]
```

**Disease groupings for curating shared pathways** (diseases in same group share pathways, enabling `find_shared_pathways` and `find_systemic_patterns` queries to return real results):

| Group | ICD-10 codes | Shared pathways |
|-------|-------------|-----------------|
| GI (17) | K29.xx, K21.0, K31.89, K52.9, K26.9, K25.7, K90.0, K63.8, K64.9, K66.0 | Gastric acid secretion, Inflammatory response, Gut microbiome |
| Hepatobiliary (8) | K80.xx, K82.8, K73.9, K71.0, K76.0, K74.x, K86.1 | Bile acid biosynthesis, Lipid metabolism, Hepatic fibrosis |
| Cardiovascular (6) | I70.9, I49.9, I10, I42.9, I80.9, I83.90 | Atherosclerosis, Lipid metabolism, Renin-angiotensin |
| Respiratory (6) | J45.9, J42, J47.9, J04.0, J02.9, J35.0, J34.2, J30.1 | Airway inflammation, Immune response |
| Musculoskeletal (6) | M19.90, M81.0, M13.0, M54.10, M75.00, M47.819, M48.27 | Bone metabolism, Inflammatory response |
| Endocrine (5) | E03.9, E04.0, E10.9, E83.01, E80.20 | Thyroid signaling, Metabolic regulation |
| Oncology (4) | C34.9, C32.0, C25.9, D13.1 | Cell cycle, Apoptosis, p53 signaling |
| Other (7) | D64.9, B83.9, G90.9, I95.9, I09.9, F48.0, N-series | Mixed |

**Estimated graph size**: ~256 nodes, ~600-800 relationships

---

## Wave 2: Neo4j Seed Script

**New file**: `api/app/seed_knowledge_graph.py`

Runnable as `python -m app.seed_knowledge_graph`. Modeled after existing `api/app/seed.py`.

**Key design decisions**:
- Uses `MERGE` everywhere (not `CREATE`) for idempotency
- Creates uniqueness constraints first (also serve as indexes)
- Synchronous Neo4j driver (one-shot script, not async)
- Reports node/relationship counts at end

**Steps**:
1. Create uniqueness constraints (`Disease.icd10`, `Pathway.name`, `NutritionalFactor.name`, etc.)
2. MERGE Pathway nodes from `PATHWAYS` dict
3. MERGE NutritionalFactor nodes from `NUTRITIONAL_FACTORS` dict
4. MERGE LifestyleIntervention nodes from `LIFESTYLE_INTERVENTIONS` dict
5. MERGE Disease nodes + all outbound relationships (PART_OF_PATHWAY, SUPPORTED_BY, RESPONDS_TO, AFFECTS, ASSOCIATED_GENE, HAS_PHENOTYPE)
6. MERGE COMORBID_WITH relationships between diseases
7. Log stats

---

## Wave 3: Makefile & Docker Integration

### 3a. Add Makefile target
**Modify**: `Makefile`
```makefile
seed-kg:
	docker compose exec api python -m app.seed_knowledge_graph
```

### 3b. Add neo4j as api dependency
**Modify**: `docker-compose.yml` — api service `depends_on`:
```yaml
neo4j:
  condition: service_healthy
```

---

## Wave 4: Pipeline Integration — Analyze Task

**Modify**: `api/app/tasks/analyze.py`

Insert **Step 5b** between risk scoring (Step 5) and recovery plan (Step 6):

```python
# Step 5b: Query knowledge graph for interventions
graph_client = GraphClient()
icd_list = list(set(e.condition_icd10 for e in entries if e.condition_icd10))

graph_nutritional = await graph_client.find_interventions(icd_list)
graph_lifestyle = await graph_client.find_lifestyle_interventions(icd_list)
all_graph_interventions = graph_nutritional + [
    {**li, "type": "lifestyle"} for li in graph_lifestyle
]
```

Then pass to planner (already accepts `graph_interventions` param):
```python
plan_data = await planner.generate_plan(
    ...,
    graph_interventions=all_graph_interventions,  # NEW
)
```

Add `graph_client.close()` in cleanup.

**Reuse**: `graph_client.py` methods already exist — `find_interventions()` and `find_lifestyle_interventions()` match the `graph_interventions` data shape that `recovery_planner.py` lines 147-159 consume.

---

## Wave 5: Pipeline Integration — Insights Router

**Modify**: `api/app/routers/insights.py`

After building the clusters list (~line 93), add:

1. **Shared pathways per cluster**: For each cluster with ≥2 ICD-10 codes, call `graph_client.find_shared_pathways(icd1, icd2)` and populate `cluster_info.shared_pathways`.

2. **Pattern cards**: Call `graph_client.find_systemic_patterns(all_icds)` to get condition pairs sharing ≥2 pathways. Convert each to a `PatternCard` with pathway names and confidence score.

Replace hardcoded `patterns=[]` (line 124) with the populated list.

---

## Wave 6: Recovery Planner Enhancement

**Modify**: `api/app/services/recovery_planner.py`

The `_generate_interventions` method (line 103) already handles `graph_interventions` but only assigns `evidence_level: "emerging"` and generic reasoning. Enhance to:

- Use the actual `evidence_level` from the graph data when available
- Include pathway names in the reasoning string
- For lifestyle interventions, set `category: "lifestyle"` and `priority: "ongoing"`
- For nutritional interventions, set `category: "nutritional"` and include condition count in reasoning

Also enhance `_generate_nutritional_recommendations` and `_generate_lifestyle_recommendations` to incorporate graph data when passed (add optional `graph_interventions` parameter).

---

## Wave 7: Verification & Tests

### 7a. Data completeness tests
**New file**: `api/tests/test_graph_seed.py`

- `test_all_normalizer_icds_have_disease_records` — every ICD-10 in `MOCK_ICD10_MAP` exists in `DISEASES`
- `test_all_diseases_have_required_fields` — every disease has ≥1 pathway and ≥1 nutritional factor
- `test_pathway_references_are_valid` — disease pathway refs exist in `PATHWAYS` dict
- `test_comorbidity_references_are_valid` — comorbid_with ICD-10 codes exist as Disease entries

### 7b. E2E verification
**Modify**: `scripts/test_e2e_pipeline.sh` — add KG verification steps:
- Check Neo4j has ≥56 Disease nodes and ≥400 relationships
- After analysis, verify insights have non-empty `shared_pathways` and `patterns`
- Verify recovery plan has graph-sourced interventions

### 7c. Manual verification
```bash
make up                   # Start services
make seed-kg              # Seed Neo4j
# Upload PDF → Analyze → Check insights page has pathway data
# Check recovery plan has graph-sourced nutritional/lifestyle recommendations
```

---

## Files Modified (Summary)

| File | Action | Description |
|------|--------|-------------|
| `api/app/data/__init__.py` | **New** | Package init |
| `api/app/data/biomedical_knowledge.py` | **New** | Curated dataset for 56+ diseases (~500 lines) |
| `api/app/seed_knowledge_graph.py` | **New** | Idempotent Neo4j seed script (~130 lines) |
| `api/app/tasks/analyze.py` | **Modify** | Add Step 5b: KG query → pass graph_interventions to planner |
| `api/app/routers/insights.py` | **Modify** | Populate shared_pathways and patterns from KG |
| `api/app/services/recovery_planner.py` | **Modify** | Enhance graph_interventions handling with evidence levels |
| `Makefile` | **Modify** | Add `seed-kg` target |
| `docker-compose.yml` | **Modify** | Add neo4j to api depends_on |
| `api/tests/test_graph_seed.py` | **New** | Data completeness tests |

**No changes needed**: `graph_client.py` (queries already work), `risk_engine.py` (pathway weight deferred to Phase 4)

## Dependency Order

```
Wave 1 (data module) → Wave 2 (seed script) → Wave 3 (Makefile/Docker)
                                 │
                                 ├→ Wave 4 (analyze.py integration)
                                 ├→ Wave 5 (insights.py integration)
                                 └→ Wave 6 (recovery_planner enhancement)
                                          │
                                          ↓
                                 Wave 7 (tests + verification)
```

Waves 1-3 are sequential. Waves 4, 5, 6 can proceed in parallel once Wave 3 is done. Wave 7 validates everything.
