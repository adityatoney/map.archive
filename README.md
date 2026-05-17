# Medical Analytics Platform

Medical analytics platform for frequency-based body scan reports. Ingests scan reports, processes them through an NLP-powered pattern recognition pipeline, and presents diagnostic insights with recovery plan recommendations.

## Architecture

```
Layer 1: Data Ingestion API        → FastAPI + Celery workers
Layer 2: NLP Embedding Engine      → BioClinical ModernBERT (HuggingFace)
Layer 3: Clinical Knowledge Graph  → Neo4j + KEGG/DisGeNET/HPO/SNOMED
Layer 4: Pattern Recognition       → Clustering, trend detection, risk scoring
Layer 5: Dashboard + Recovery Plan → Next.js 14 + shadcn/ui + Recharts
```

## Prerequisites

- Docker & Docker Compose
- (Optional) Node.js 20+ and Python 3.11+ for local development without Docker

## Quick Start

```bash
# 1. Clone and enter directory
cd medical.analytics.platform

# 2. Start all services
make up

# 3. Run database migrations
make migrate

# 4. Seed demo data
make seed

# 5. Open the dashboard
open http://localhost:3000
```

**Demo login:** `demo@medbed.local` / `demo123`

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:3000 | Next.js frontend |
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Neo4j Browser | http://localhost:7474 | Knowledge graph |
| ML Service | http://localhost:8001 | BioClinical ModernBERT (optional) |

## Make Commands

```bash
make up          # Start all services
make down        # Stop all services
make up-ml       # Start with ML service (downloads ~600MB model)
make logs        # Tail service logs
make migrate     # Run database migrations
make seed        # Populate demo data
make test-api    # Run backend tests
make test-web    # Run frontend tests
make lint        # Run linters
make db-shell    # PostgreSQL shell
make clean       # Stop services and remove volumes
```

## Project Structure

```
medical.analytics.platform/
├── api/                 # FastAPI backend
│   ├── app/
│   │   ├── models/      # SQLAlchemy models (Patient, ScanSession, ScanEntry, etc.)
│   │   ├── routers/     # API endpoints (auth, reports, patients, insights, recovery)
│   │   ├── services/    # Business logic (parser, normalizer, embedder, clusterer)
│   │   ├── tasks/       # Celery async tasks (analysis pipeline)
│   │   └── utils/       # Auth, encryption helpers
│   ├── migrations/      # Alembic database migrations
│   └── tests/           # Pytest test suite
├── web/                 # Next.js 14 frontend
│   └── src/
│       ├── app/         # App Router pages (dashboard, report, trends, insights, recovery)
│       ├── components/  # shadcn/ui + custom components
│       └── lib/         # API client, Zustand stores, TanStack Query hooks
├── ml/                  # ML model serving
│   └── serve/           # BioClinical ModernBERT FastAPI service
├── infra/               # Infrastructure (DB init scripts)
├── docker-compose.yml   # Local development stack
└── Makefile             # Common commands
```

## API Endpoints

```
POST   /api/v1/auth/login              # Authenticate user
POST   /api/v1/reports/upload           # Upload scan report (PDF/CSV/JSON/image)
GET    /api/v1/reports/{session_id}     # Get parsed report with entries
POST   /api/v1/reports/{session_id}/analyze  # Trigger analysis pipeline
POST   /api/v1/reports/compare          # Compare two sessions
GET    /api/v1/patients/                # List patients
GET    /api/v1/patients/{id}/history    # Patient scan history
GET    /api/v1/insights/{session_id}    # Diagnostic insights
GET    /api/v1/recovery/{session_id}    # Recovery plan
GET    /health                          # Health check
```

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

- `ENCRYPTION_KEY` — Fernet key for PHI encryption at rest
- `UMLS_API_KEY` — Set to `mock` for local dev, real key for production
- `MODEL_NAME` — BioClinical ModernBERT variant (base for dev, large for prod)
- `NEO4J_ENABLED` — Set to `false` to skip Neo4j dependency

## Medical Disclaimer

Medical Analytics Platform is an analytical exploration tool, not a medical diagnostic device. The information presented is derived from frequency-based scan data analysis and pattern recognition algorithms. It does not constitute medical advice, diagnosis, or treatment recommendations. Always consult a qualified healthcare professional before making health decisions.
