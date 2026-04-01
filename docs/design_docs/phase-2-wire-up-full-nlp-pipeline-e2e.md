# Phase 2: Wire Up Full NLP Pipeline End-to-End

## Context

Phase 1 established the full foundation: monorepo, Docker Compose stack, FastAPI backend, Next.js frontend, and ML service stub. All pipeline services exist (`embedder.py`, `clusterer.py`, `risk_engine.py`, `recovery_planner.py`) and the Celery task (`analyze.py`) already orchestrates all 7 steps. However, the ML service never starts by default (behind `profiles: ["ml"]`), so embeddings always fall back to deterministic mocks, producing trivial clusters.

**Goal**: Wire the pipeline so that when the ML service is running, real BioClinical-ModernBERT embeddings flow through → pgvector → HDBSCAN/UMAP → meaningful clusters. Uploading the real 26-page PDF should produce real analysis results.

---

## Wave 1: ML Service Reliability

### 1a. Make `BATCH_SIZE` configurable via env var
**File**: `ml/serve/config.py`
- Change `BATCH_SIZE: int = 32` → `BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "16"))`
- 16 is safer for CPU (Apple Silicon); GPU users can override via `.env`

### 1b. Add per-batch progress logging to ML handler
**File**: `ml/serve/handler.py`
- In `_generate_embeddings`, log each batch: `"Embedding batch %d/%d (%d texts)"`
- Log total timing at end: `"Embedded %d texts in %.1f seconds"`

### 1c. Add healthcheck for ML service in Docker Compose
**File**: `docker-compose.yml`
- Add under `ml` service:
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 30s
  ```

### 1d. Add Makefile targets
**File**: `Makefile`
- `up-full` — `docker compose --profile ml up -d`
- `warm-model` — curl POST to `/embed` with a test text to trigger model download
- `ml-health` — curl `/health` and pretty-print
- `ml-logs` — `docker compose --profile ml logs -f ml`

---

## Wave 2: Embedder Service Robustness

**File**: `api/app/services/embedder.py`

### 2a. Increase timeout to 120s and add model warm-up logic
- Before sending the full batch, check `GET /health` on the ML service
- If `model_loaded: false`, send a single warm-up text with 300s timeout (covers model download)
- Main batch request uses 120s timeout (covers ~60s embedding of 426 entries)

### 2b. Add `is_ml_service_available()` method
- Quick health check method that returns `bool`
- Used by the Celery task to log and track embedding source

### 2c. Log real vs mock embedding usage
- On success: `logger.info("Got %d real embeddings from ML service", count)`
- On fallback: already logged (existing warning)

---

## Wave 3: Clustering Parameter Tuning

**File**: `api/app/services/clusterer.py`

### 3a. Dynamic parameter selection based on dataset size
Add `_compute_params(n)` method:
| Dataset size | min_cluster_size | n_neighbors | UMAP intermediate dims |
|---|---|---|---|
| n < 30 | 2 | min(5, n-1) | min(10, n-1) |
| 30 ≤ n < 100 | 3 | min(10, n-1) | min(30, n-1) |
| 100 ≤ n < 300 | 5 | 15 | 50 |
| n ≥ 300 | 8 | 15 | 50 |

### 3b. Add `cluster_selection_epsilon=0.05` to HDBSCAN
- Merges nearby micro-clusters to prevent over-fragmentation with real biomedical embeddings

### 3c. Noise fallback
- If >80% of entries are noise (label -1), rerun with `min_cluster_size=2`
- Guarantees at least some meaningful clusters

### 3d. Accept `organ_systems` parameter for richer cluster summaries
- Update `cluster_entries()` signature to accept optional `organ_systems: list[str]`
- Include dominant organ system in each cluster summary dict

---

## Wave 4: Database Migration — New Columns on ScanSession

### 4a. Add columns to ScanSession model
**File**: `api/app/models/session.py`
- `cluster_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)` — stores full cluster result (UMAP coords, cluster summaries, labels)
- `embedding_source: Mapped[str | None] = mapped_column(String(20), nullable=True)` — "real" or "mock"

### 4b. Generate and run Alembic migration
- `make migration msg="add_cluster_metadata_and_embedding_source"`
- `make migrate`

---

## Wave 5: Celery Pipeline Updates

**File**: `api/app/tasks/analyze.py`

### 5a. Track embedding source
- Before Step 3, check `embedder.is_ml_service_available()`
- After embedding, determine if real or mock was used (check if ML service responded)
- Set `session.embedding_source = "real" | "mock"`

### 5b. Persist cluster metadata on session
- After Step 4 (clustering), store the full `cluster_result` dict on `session.cluster_metadata`
- This preserves UMAP coords, cluster summaries, and labels for the API/frontend

### 5c. Pass organ_systems to clusterer
- In Step 4, pass `organ_systems=[e.organ_system for e in entries]` to `cluster_entries()`

### 5d. Add task time limit
- Add `soft_time_limit=600` to `@celery.task` decorator (10 min ceiling for full pipeline)

---

## Wave 6: API Enhancements

### 6a. Update insights endpoint with UMAP coords
**File**: `api/app/routers/insights.py`
- Load `session.cluster_metadata` and include `umap_coords` in response
- Add `embedding_source` to response

### 6b. Update report endpoint with embedding_source
**File**: `api/app/routers/reports.py`
- Add `embedding_source: str | None` to `SessionOut` response model

### 6c. Add ML service status to health endpoint
**File**: `api/app/main.py`
- Add async check to ML service in `/health` response: `"ml_service": "available" | "unavailable"`

---

## Wave 7: Frontend Polish

### 7a. Auto-poll report status during analysis
**File**: `web/src/lib/hooks/use-api.ts`
- Add `refetchInterval` option to `useReport` — poll every 3s while `analysis_status === "processing"`

**File**: `web/src/app/dashboard/report/[id]/page.tsx`
- Show progress indicator while processing
- Auto-refresh when status changes to "completed"

### 7b. Show embedding source badge
**File**: `web/src/app/dashboard/report/[id]/page.tsx`
- Small badge: "Real Embeddings ✓" (green) or "Mock Embeddings" (gray)

### 7c. Update insights page for UMAP data
**File**: `web/src/lib/api-client.ts`
- Add `umap_coords` and `embedding_source` to `InsightsData` type

---

## Wave 8: End-to-End Verification

### Create verification script
**File**: `scripts/test_e2e_pipeline.sh`

Steps:
1. Check ML service health → `model_loaded: true`
2. Upload `docs/sample_docs/sample_report.pdf` via API
3. Trigger analysis → `POST /analyze`
4. Poll until `analysis_status === "completed"` (timeout: 5min)
5. Verify: entry count > 100, `embedding_source === "real"`
6. Verify: insights have UMAP coords, ≥3 distinct clusters
7. Verify: recovery plan exists with non-empty summary

### Manual verification
```bash
make up-full              # Start all services including ML
make warm-model           # Trigger model download (~600MB, first time only)
make ml-health            # Confirm model_loaded: true
# Login at http://localhost:3010 → Upload sample PDF → View report
# Should see "Real Embeddings" badge, meaningful clusters in insights
```

---

## Files Modified (Summary)

| File | Change |
|------|--------|
| `ml/serve/config.py` | Env-configurable BATCH_SIZE (default 16) |
| `ml/serve/handler.py` | Batch progress logging |
| `docker-compose.yml` | ML service healthcheck |
| `Makefile` | `up-full`, `warm-model`, `ml-health`, `ml-logs` targets |
| `api/app/services/embedder.py` | 120s timeout, warm-up logic, `is_ml_service_available()` |
| `api/app/services/clusterer.py` | Dynamic params, epsilon, noise fallback, organ_systems param |
| `api/app/models/session.py` | `cluster_metadata` (JSON) and `embedding_source` (String) columns |
| `api/app/tasks/analyze.py` | Persist cluster metadata, track embedding source, time limit |
| `api/app/routers/insights.py` | Return UMAP coords and embedding_source |
| `api/app/routers/reports.py` | Return embedding_source in session response |
| `api/app/main.py` | ML service status in /health |
| `web/src/lib/hooks/use-api.ts` | Auto-poll during analysis |
| `web/src/lib/api-client.ts` | Updated types for UMAP/embedding_source |
| `web/src/app/dashboard/report/[id]/page.tsx` | Polling, embedding badge |
| New: `scripts/test_e2e_pipeline.sh` | E2E verification script |
| New: Alembic migration | `cluster_metadata` + `embedding_source` columns |

## Dependency Order

```
Wave 1 (ML service) ─┐
Wave 3 (Clusterer)  ─┼─→ Wave 5 (Celery pipeline) → Wave 6 (API) → Wave 7 (Frontend)
Wave 4 (Migration)  ─┘                                                    ↓
                                                                    Wave 8 (E2E test)
Wave 2 (Embedder) ──→ Wave 5
```

Waves 1, 2, 3, 4 can be done in parallel. Wave 5 requires all four. Waves 6-7 require Wave 5. Wave 8 is last.
