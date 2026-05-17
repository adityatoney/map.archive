# Phase 5: Frontend Visualizations & Data Wiring

## Context

Phases 1-4 are complete. The Medical Analytics Platform has a full working pipeline (PDF → parse → normalize → embed → cluster → trend → composite risk → KG query → recovery plan → LLM clinical analysis) with all backend APIs functional and all frontend pages working **except four placeholder/stub areas** marked "coming in Phase 5":

1. **Trends page** — shows mock data, not wired to backend
2. **UMAP cluster scatter plot** — placeholder in report + insights pages
3. **Body map risk overlay** — placeholder on main dashboard
4. **Knowledge graph explorer** — placeholder in insights page

This phase completes these four features using **no new dependencies** (recharts already installed, SVG for custom visualizations).

---

## Feature 1: Trends Page (Highest Priority)

**Why first:** This is the only broken page — it shows fake data to users. All other placeholders are clearly labeled.

### Nav routing fix
**File:** `web/src/app/dashboard/layout.tsx`
- The trends page needs a `patient_id` (line 24 comment confirms this), but the nav currently passes `latestSessionId` (line 98-99).
- Add a `usePatientId` flag to the trends nav item, or special-case it: if `item.href === "/dashboard/trends"`, use `selectedPatientId` instead of `latestSessionId`.

### API types + method
**File:** `web/src/lib/api-client.ts`
- Add `TrendItem` interface: `condition_name`, `condition_icd10`, `organ_system`, `trend_direction` (improving/worsening/stable/volatile), `trend_slope`, `sessions_analyzed`, `first_score`, `last_score`, `change_points`
- Add `PatientTrendsData` interface: `patient_id`, `trends: TrendItem[]`, `total_trends`, `summary: {improving, worsening, stable, volatile}`
- Add method `getPatientTrends(patientId: string)` → `GET /api/v1/patients/${patientId}/trends`

### Hook
**File:** `web/src/lib/hooks/use-api.ts`
- Add `usePatientTrends(patientId)` following existing patterns

### Page rewrite
**File:** `web/src/app/dashboard/trends/[id]/page.tsx` — full rewrite
- Fetch real data via `usePatientTrends(params.id)`
- **Empty state:** If 0 trends, show info card: "Trend analysis requires 2+ analyzed sessions"
- **Summary cards:** Wire to `trends.summary` (improving/worsening/stable/volatile counts)
- **Sparkline grid:** Per-condition mini line charts using recharts `LineChart` with data built from `first_score`, `change_points`, `last_score`. Color by direction.
- **Detail cards:** Expandable cards sorted by |slope| showing condition name, organ badge, direction icon, slope, session count, score delta

### New component
**File to create:** `web/src/components/charts/trend-sparkline.tsx`
- Reusable recharts `LineChart` (tiny, no axes) accepting `dataPoints` and `direction`

---

## Feature 2: UMAP Cluster Scatter Plot (High Priority)

**Why second:** Replaces two visible placeholders, data already exists in backend.

### Backend enrichment
**File:** `api/app/routers/insights.py`
- Add `ScatterPoint` model: `condition_name`, `x`, `y`, `cluster_id`, `score`, `organ_system`, `risk_tier`
- Add optional `scatter_data: list[ScatterPoint] | None` to `InsightsResponse`
- After extracting `umap_coords` (line 195-197), zip with entries to build `scatter_data`

### Frontend types
**File:** `web/src/lib/api-client.ts`
- Add `ScatterPoint` interface and `scatter_data` field to `InsightsData`

### New component
**File to create:** `web/src/components/charts/cluster-scatter.tsx`
- recharts `ScatterChart` with one `Scatter` series per cluster ID, each with distinct color
- Custom tooltip: condition name, score, organ system, risk tier
- `onClick` callback for filtering
- Hide axes (UMAP coords aren't meaningful)

### Integration
- **Insights page** (`web/src/app/dashboard/insights/[id]/page.tsx`): Add scatter plot section between risk summary and cluster cards
- **Report page** (`web/src/app/dashboard/report/[id]/page.tsx`): Replace cluster viz placeholder (line ~1149). Fetch insights data via `useInsights(sessionId)`.

---

## Feature 3: Body Map Risk Overlay (Medium Priority)

**Why third:** Visual polish on the most-visited page (dashboard).

### New component
**File to create:** `web/src/components/charts/body-map.tsx`
- SVG body silhouette (300×500 viewBox) with colored organ regions
- Map organ system names → SVG region paths/ellipses
- Color by risk tier: critical=red, high=orange, moderate=amber, low=green, no data=gray
- Hover tooltip (shadcn `Tooltip`): organ name + risk score + condition count
- Click navigates to insights page

### Dashboard integration
**File:** `web/src/app/dashboard/page.tsx`
- Call `useInsights(latestSessionId)` to get `risk_summary`
- Replace placeholder card (line ~186) with `BodyMap` component
- Skeleton state while loading

---

## Feature 4: Knowledge Graph Mini-Explorer (Lower Priority)

**Why last:** Requires a new backend endpoint + most complex visualization.

### New backend endpoint
**File to create:** `api/app/routers/graph.py`
- `GET /api/v1/graph/context?icd_codes=X,Y,Z&depth=1`
- Returns `GraphContextResponse`: `nodes: [{id, label, type}]`, `edges: [{source, target, relationship}]`
- Queries Neo4j via existing `GraphClient.get_condition_context()`
- Cap at 50 nodes to keep visualization manageable

### Register router
**File:** `api/app/main.py` — add graph router

### Frontend types + hook
**File:** `web/src/lib/api-client.ts` — add `GraphNode`, `GraphEdge`, `GraphContextData`, `getGraphContext()`
**File:** `web/src/lib/hooks/use-api.ts` — add `useGraphContext(icdCodes)`

### New component
**File to create:** `web/src/components/charts/graph-explorer.tsx`
- Static radial SVG layout (no D3 needed)
- Disease nodes in outer ring, pathway nodes in inner ring
- Curved SVG bezier paths for edges
- Color nodes by type: disease=blue, pathway=purple, intervention=green
- Hover tooltips, click callbacks

### Integration
**File:** `web/src/app/dashboard/insights/[id]/page.tsx`
- Extract ICD-10 codes from clusters data
- Call `useGraphContext(icdCodes)`
- Replace KG placeholder (line ~164) with `GraphExplorer`

---

## Files Summary

| File | Action | Feature |
|------|--------|---------|
| `web/src/app/dashboard/layout.tsx` | Modify | F1 (trends nav fix) |
| `web/src/lib/api-client.ts` | Modify | F1, F2, F4 (types + methods) |
| `web/src/lib/hooks/use-api.ts` | Modify | F1, F4 (hooks) |
| `web/src/app/dashboard/trends/[id]/page.tsx` | Rewrite | F1 |
| `web/src/components/charts/trend-sparkline.tsx` | **Create** | F1 |
| `api/app/routers/insights.py` | Modify | F2 (add scatter_data) |
| `web/src/components/charts/cluster-scatter.tsx` | **Create** | F2 |
| `web/src/app/dashboard/insights/[id]/page.tsx` | Modify | F2, F4 |
| `web/src/app/dashboard/report/[id]/page.tsx` | Modify | F2 (scatter plot) |
| `web/src/components/charts/body-map.tsx` | **Create** | F3 |
| `web/src/app/dashboard/page.tsx` | Modify | F3 (body map) |
| `api/app/routers/graph.py` | **Create** | F4 |
| `api/app/main.py` | Modify | F4 (register router) |
| `web/src/components/charts/graph-explorer.tsx` | **Create** | F4 |

## Verification

1. **Trends:** Navigate to trends page with a patient that has 1 session → see "needs more data" message. Upload 2nd scan, re-analyze → see real sparklines and summary cards.
2. **Scatter:** Navigate to insights page → see colored UMAP scatter plot with tooltips. Click a dot → filter cluster cards.
3. **Body map:** Dashboard shows colored organ regions. Hover shows risk info. Click navigates to insights.
4. **KG explorer:** Insights page shows network graph of conditions connected by shared pathways.
5. **No regressions:** All existing pages still work. No new npm dependencies needed.
