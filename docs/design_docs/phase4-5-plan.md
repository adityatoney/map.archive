# Phase 4–5 Implementation Plan

## Status as of 2026-04-01

### Completed
- **Phase 1 — Foundation**: Monorepo, PostgreSQL+pgvector, FastAPI, Celery, Next.js shell, Docker Compose, auth, PDF parsing
- **Phase 2 — NLP Pipeline**: BioClinical ModernBERT embeddings, HDBSCAN clustering, UMAP dimensionality reduction, ICD-10/SNOMED/FMA normalization, risk scoring, template-based recovery plans
- **Phase 3 — Knowledge Graph**: Neo4j seeded with 493 nodes / 1,354 relationships (67 diseases, 43 pathways, 30 nutritional factors, 25 lifestyle interventions, 112 genes, 138 phenotypes, 78 anatomical structures). Graph queries wired into analysis pipeline — recovery plans include graph-sourced interventions, insights endpoint returns pattern cards with shared biological pathways.

---

## Phase 4: Insights & Recovery Plan Engine (remaining work)

### 4a. Temporal Trend Analysis
**Priority**: High
**Effort**: Medium
**Files**: `api/app/tasks/analyze.py`, `api/app/services/trend_analyzer.py`, `api/app/models/trend.py`

The `TrendAnalyzerService` and `ConditionTrend` model exist but are not wired into the pipeline. Wire them in so that when a patient has multiple scan sessions, the pipeline:
1. After clustering (Step 4), query previous sessions for the same patient
2. Compute per-condition linear regression slopes (improving/worsening/stable)
3. Run PELT change-point detection for sudden shifts
4. Persist `ConditionTrend` records to the database
5. Expose trends via `GET /api/v1/patients/{id}/trends` endpoint

**Depends on**: Nothing — can start immediately.

---

### 4b. Composite Risk Scoring with KG Pathway Weight
**Priority**: Medium
**Effort**: Low
**Files**: `api/app/services/risk_engine.py`

Current risk scoring uses simple score thresholds. Upgrade to the design doc's composite formula:
- 40% current severity (average score)
- 25% trend direction (from 4a — default to 0 if no prior sessions)
- 20% cluster density (number of conditions in same cluster)
- 15% KG pathway load (number of shared pathways from Neo4j)

**Depends on**: 4a (for trend component), though can stub the trend weight initially.

---

### 4c. LLM-Powered Recovery Plan Summaries
**Priority**: Medium
**Effort**: Low
**Files**: `api/app/services/recovery_planner.py`, `api/app/config.py`

The `_generate_summary` method currently uses string templates. Replace with an Anthropic Claude API call that takes the structured plan data and produces a natural-language 2–3 paragraph summary. Fall back to template if no API key is configured.

**Requires**: `ANTHROPIC_API_KEY` environment variable.
**Depends on**: Nothing — can start immediately.

---

## Phase 5: Dashboard UI (frontend visualizations)

### 5a. UMAP Cluster Visualization
**Priority**: Highest
**Effort**: Low
**Files**: `web/src/app/dashboard/report/[sessionId]/page.tsx` (or a new component)

Data already exists in `session.cluster_metadata.umap_coords`. Build a D3.js 2D scatter plot:
- Each dot = one condition, colored by cluster ID
- Tooltip on hover showing condition name, score, organ system
- Noise points (cluster -1) in grey
- Click to highlight all conditions in same cluster

**Depends on**: Nothing — data is already in the API response.

---

### 5b. Temporal Trend Sparklines
**Priority**: High
**Effort**: Medium
**Files**: `web/src/app/dashboard/trends/[patientId]/page.tsx`

Build a Recharts sparkline grid showing per-condition score trajectories across sessions:
- One sparkline per condition (sorted by most recent score)
- Color-coded by trend direction (green=improving, red=worsening, grey=stable)
- Trend summary cards at top (X improving, Y worsening, Z new, W resolved)
- Session selector/slider for comparing specific timepoints

**Depends on**: 4a (trend data in API).

---

### 5c. Knowledge Graph Explorer
**Priority**: High
**Effort**: Medium–High
**Files**: New component, likely `web/src/components/graph-explorer.tsx`

D3.js force-directed graph visualization:
- Nodes: diseases (by cluster), pathways, nutritional factors, lifestyle interventions
- Edges: PART_OF_PATHWAY, SUPPORTED_BY, RESPONDS_TO
- Filter by organ system or cluster
- Click a disease to expand its graph neighborhood
- Needs a new API endpoint: `GET /api/v1/graph/{icd10}/context` (wraps `graph_client.get_condition_context`)

**Depends on**: Nothing for the backend (graph_client methods exist). Frontend-only work.

---

### 5d. Body Map Risk Overlay
**Priority**: Medium
**Effort**: Medium
**Files**: New SVG component, `web/src/components/body-map.tsx`

SVG body silhouette with organ system regions colored by risk tier:
- Low=green, moderate=yellow, high=orange, critical=red
- Click an organ region to filter the condition table
- Tooltip showing organ system name, risk score, condition count
- Data source: `risk_summary` from insights endpoint

**Depends on**: Nothing — data already available.

---

### 5e. Session Comparison View
**Priority**: Low
**Effort**: Medium
**Files**: `web/src/app/dashboard/compare/page.tsx`

Side-by-side comparison of two sessions:
- Delta highlighting (score increased/decreased)
- Radar chart comparing organ system risk profiles
- New/resolved conditions highlighted
- Backend endpoint already exists: `POST /api/v1/reports/compare`

**Depends on**: Nothing — API exists.

---

## Recommended Execution Order

```
4a (Temporal Trends) ──→ 4b (Composite Risk) ──→ 5b (Trend Sparklines)
                    \
4c (LLM Summaries)   ──→ independent
5a (UMAP Viz)        ──→ independent, start first (quick win)
5c (Graph Explorer)  ──→ independent
5d (Body Map)        ──→ independent
5e (Session Compare) ──→ independent, lowest priority
```

**Suggested sprint plan**:
1. **Sprint 1**: 5a (UMAP viz) + 4a (temporal trends) + 4c (LLM summaries)
2. **Sprint 2**: 5b (trend sparklines) + 5c (graph explorer) + 4b (composite risk)
3. **Sprint 3**: 5d (body map) + 5e (session comparison) + polish

---

## Infrastructure Notes
- All services run via `docker compose up -d`
- Neo4j seeding: `make seed-kg` (idempotent)
- Tests: `docker compose exec api python -m pytest tests/ -v`
- Demo login: `demo@medbed.local` / `demo123`
- ML service (optional): `docker compose --profile ml up -d`
- Existing session with full analysis: `ffadb9c8-97b1-454b-a19e-3555e7162663`
