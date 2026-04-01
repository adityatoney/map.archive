# MedBed Insight Analytics Platform — Phase 1 Implementation Plan

## Context
Building a greenfield full-stack medical analytics platform that ingests Tesla Med Bed frequency-based body scan reports, processes them through an NLP pipeline, and presents diagnostic insights via an interactive dashboard. This Phase 1 establishes the complete foundation: monorepo structure, Docker Compose local dev stack, FastAPI backend with PostgreSQL schema, Next.js 14 frontend shell, and ML model serving setup.

**Key constraints**: Docker Compose only (no cloud IaC), BioClinical-ModernBERT-base for local dev (config to swap to large in prod), all external services mocked (no API keys), medical disclaimer on every page, PHI encryption at rest.

---

## Implementation Waves

### Wave 0: Root Monorepo Scaffolding

**Files to create:**
- `.gitignore`, `.env.example`, `README.md`, `Makefile`
- `docker-compose.yml` with services:
  | Service | Image | Ports |
  |---------|-------|-------|
  | `db` | `pgvector/pgvector:pg16` | 5432 |
  | `redis` | `redis:7-alpine` | 6379 |
  | `neo4j` | `neo4j:5-community` | 7474, 7687 |
  | `api` | build `./api` | 8000 |
  | `celery-worker` | build `./api` | — |
  | `web` | build `./web` | 3000 |
  | `ml` | build `./ml` (profile: ml) | 8001 |
- DB init script to enable `pgvector` and `uuid-ossp` extensions
- Named volumes: `pgdata`, `redisdata`, `neo4jdata`, `model_cache`, `uploads`

**Makefile targets**: `up`, `down`, `up-ml`, `logs`, `migrate`, `migration`, `seed`, `test-api`, `test-web`

---

### Wave 1: Backend Core

**`api/app/config.py`** — `pydantic-settings.BaseSettings`:
- DB/Redis/Neo4j connection strings
- `ENCRYPTION_KEY` (Fernet), `ML_SERVICE_URL`, `MODEL_NAME` (base/large swap)
- Mock mode flags: `UMLS_API_KEY=mock`, `ANTHROPIC_API_KEY=mock`, `NEO4J_ENABLED=true`

**SQLAlchemy Models** (`api/app/models/`):
- `base.py` — async engine, session factory, declarative base with pgvector
- `user.py` — User (id, email, hashed_password) for auth
- `patient.py` — Patient (id, name as Fernet-encrypted text, created_at)
- `session.py` — ScanSession (id, patient_id FK, scan_date, raw_report_url, organ_system)
- `entry.py` — ScanEntry (id, session_id FK, condition_name, condition_icd10, condition_snomed, anatomical_location, anatomical_fma_id, score, green_ratio, red_ratio, embedding_vector Vector(768), cluster_id, risk_tier)
- `trend.py` — ConditionTrend (id, patient_id FK, condition_icd10, trend_direction, trend_slope, change_points JSON)
- `recovery.py` — RecoveryPlan (id, session_id FK, patient_id FK, summary text, all JSON fields, disclaimer)

**`api/app/utils/encryption.py`** — Fernet encrypt/decrypt helpers for PHI

**Alembic** — async migration setup, initial migration creating all tables + extensions

**`api/app/main.py`** — FastAPI app factory with CORS (`localhost:3000`), health check, router registration

**`api/Dockerfile`** — Python 3.11-slim with `tesseract-ocr`, `poppler-utils`, `libpq-dev`

---

### Wave 2: API Routes + Services

**Routers** (`api/app/routers/`):
- `auth.py` — `POST /api/v1/auth/login` returns JWT; demo user `demo@medbed.local`/`demo123`
- `reports.py` — upload, get report, analyze, insights, compare endpoints
- `patients.py` — patient history endpoint
- `insights.py`, `recovery.py`, `compare.py` — delegate to services

**Auth middleware** — JWT validation on all `/api/v1/` routes except health and auth

**Services** (`api/app/services/`):
| Service | Phase 1 Status | Mock Pattern |
|---------|---------------|--------------|
| `parser.py` | **Full implementation** — PDF (pytesseract+pdf2image), CSV (pandas), JSON, image OCR | N/A |
| `normalizer.py` | **Mock fallback** — hardcoded dict of ~20-30 common MedBed conditions → ICD-10/SNOMED | `UMLS_API_KEY == "mock"` → use lookup dict |
| `embedder.py` | **Mock fallback** — calls ML service HTTP; on failure returns deterministic hash-seeded 768-dim vectors | HTTP call fails → mock vectors |
| `graph_client.py` | **Mock fallback** — Neo4j driver wrapper; returns empty results when unavailable | Connection failure → empty results + warning |
| `clusterer.py` | **Stub** — HDBSCAN+UMAP interface; assigns all to cluster 0 with mocks | Returns trivial clusters |
| `trend_analyzer.py` | **Stub** — correct signatures, returns placeholder data | — |
| `risk_engine.py` | **Stub** — correct signatures, returns placeholder data | — |
| `recovery_planner.py` | **Stub** — correct signatures, returns template text | — |

**Celery** (`api/app/celery_app.py` + `api/app/tasks/analyze.py`):
- Redis broker
- `run_analysis_pipeline(session_id)`: load entries → normalize → embed → cluster → update DB

**File storage**: Docker volume `/app/uploads/` for uploaded reports (no S3 in Phase 1)

---

### Wave 3: Frontend Shell (parallel with Wave 2)

**Scaffold**: `create-next-app` with TypeScript, Tailwind, App Router

**Dependencies**: shadcn/ui, next-auth, zustand, @tanstack/react-query, recharts, lucide-react

**`web/app/layout.tsx`** — Root: QueryClientProvider, SessionProvider, theme provider (dark/light)

**`web/app/api/auth/[...nextauth]/route.ts`** — CredentialProvider calling FastAPI login, stores JWT in session

**`web/app/dashboard/layout.tsx`** — Authenticated wrapper:
- Header: logo, patient selector dropdown, dark/light toggle, user menu
- Sidebar: nav links (Dashboard, Upload, Trends, Insights, Recovery, Compare)
- **Medical Disclaimer Banner**: fixed-position, non-dismissible amber strip at viewport bottom

**Page shells** (all under `web/app/dashboard/`):
1. `page.tsx` — Overview: metric cards, body map placeholder, quick actions
2. `report/[id]/page.tsx` — Condition table, cluster viz placeholder, score distribution
3. `trends/[id]/page.tsx` — Sparkline grid area, trend summary cards
4. `insights/[id]/page.tsx` — Pattern cards, knowledge graph placeholder
5. `recovery/[id]/page.tsx` — Summary, priority conditions, interventions + **inline disclaimer**
6. `compare/page.tsx` — Two session selectors, side-by-side comparison area

**`web/lib/api-client.ts`** — Typed fetch wrapper with auth token injection from NextAuth session

**Zustand stores**: `patient-store.ts`, `report-store.ts`, `ui-store.ts`

**TanStack Query hooks**: `useReport()`, `usePatientHistory()`, `useInsights()`, etc.

**`web/Dockerfile`** — Node 20-alpine, dev mode

---

### Wave 4: ML Service

**`ml/serve/config.py`** — `MODEL_NAME` env var (default: `BioClinical-ModernBERT-base`, prod: large), device auto-detect

**`ml/serve/handler.py`** — FastAPI with:
- `POST /embed` — accepts `{"texts": [...]}`, returns `{"embeddings": [...]}`
- `GET /health` — model loaded status
- **Lazy loading**: model loads on first `/embed` request (avoids blocking Docker startup)

**`ml/serve/requirements.txt`** — torch, transformers, sentence-transformers, fastapi, uvicorn

**`ml/Dockerfile`** — Python 3.11-slim, model_cache volume for HuggingFace cache persistence

ML service is **optional** via Docker Compose profile (`docker compose --profile ml up`)

---

### Wave 5: Integration & Seed Data

**`api/app/seed.py`**:
- Creates demo user (demo@medbed.local)
- Creates demo patient (encrypted name)
- Creates 2-3 sample scan sessions with realistic MedBed entries (~10 entries each)
- Populates mock ICD-10/SNOMED codes

**Sample fixture**: `api/tests/fixtures/sample_report.csv` with ~10 MedBed condition entries

**End-to-end flow**: `make up` → `make migrate` → `make seed` → login → upload CSV → view report

---

### Wave 6: Testing Foundation

**API tests** (`api/tests/`):
- `conftest.py` — async test client, test DB setup
- `test_health.py` — health endpoint returns 200
- `test_upload.py` — CSV upload creates session + entries
- `test_parser.py` — unit tests for CSV/JSON parser
- `test_encryption.py` — PHI encrypt/decrypt round-trip
- `test_normalizer.py` — mock normalizer returns expected codes
- `test_auth.py` — JWT login flow

**Frontend tests**: Jest + RTL, verify disclaimer renders, API client mock tests

---

## Key Design Decisions

1. **Mock/fallback architecture**: Every external service has a mock mode via config flag. Pattern: `if self.mock_mode: return self._mock_impl()` — enables full local dev without any API keys
2. **ML lazy loading**: Model loads on first request, not startup. Avoids Docker health check timeouts. `model_cache` volume persists the ~600MB download
3. **PHI encryption**: Fernet symmetric encryption in repository layer (explicit encrypt/decrypt calls, not magic type decorators)
4. **Disclaimer strategy**: Global non-dismissible amber banner in dashboard layout + inline stronger disclaimer on recovery plan page
5. **File storage**: Local Docker volume in Phase 1, S3 presigned URLs in later phase
6. **Auth flow**: NextAuth CredentialProvider → FastAPI JWT login → JWT stored in NextAuth session → passed as Bearer token to API

## File Creation Order (Optimal)

```
1. .gitignore, .env.example, README.md, Makefile
2. docker-compose.yml, infra/init-db.sql
3. api/requirements.txt, api/Dockerfile, api/alembic.ini
4. api/app/config.py, api/app/models/ (all models)
5. api/app/utils/encryption.py
6. api/migrations/env.py → run initial migration
7. api/app/main.py (app factory + health check)
8. api/app/routers/ (auth, reports, patients, insights, recovery, compare)
9. api/app/services/ (parser full, normalizer mock, embedder mock, others stub)
10. api/app/celery_app.py, api/app/tasks/analyze.py
11. ml/serve/ (config, handler, requirements), ml/Dockerfile
── frontend in parallel from step 7 ──
12. web/ scaffold (create-next-app + deps)
13. web/app/layout.tsx, auth route, dashboard/layout.tsx
14. web/lib/ (api-client, stores, query hooks)
15. web/app/dashboard/ (all page shells)
16. api/app/seed.py, api/tests/fixtures/
17. api/tests/, web tests
```

## Verification

1. `make up` — all services start without errors
2. `make migrate` — DB tables created with pgvector extension
3. `make seed` — demo data populated
4. `curl localhost:8000/health` — returns `{"status": "ok"}`
5. Login at `localhost:3000` with demo@medbed.local/demo123
6. Medical disclaimer visible on every dashboard page
7. Upload `sample_report.csv` via dashboard → entries appear in report view
8. `POST /api/v1/reports/{id}/analyze` → Celery task completes (mock pipeline)
9. `make test-api` — all backend tests pass
10. `docker compose --profile ml up ml` → `curl localhost:8001/health` returns ok
