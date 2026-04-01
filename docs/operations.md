# MedBed Insight — Operations Guide

## Port Mapping

| Service     | Container Port | Host Port | URL                          |
|-------------|---------------|-----------|------------------------------|
| Web (Next.js) | 3000        | **3010**  | http://localhost:3010        |
| API (FastAPI) | 8000        | **8010**  | http://localhost:8010        |
| ML Service    | 8001        | **8001**  | http://localhost:8001        |
| PostgreSQL    | 5432        | **5435**  | `postgresql://medbed:medbed@localhost:5435/medbed` |
| Redis         | 6379        | **6379**  | `redis://localhost:6379`     |
| Neo4j Browser | 7474        | **7474**  | http://localhost:7474        |
| Neo4j Bolt    | 7687        | **7687**  | `bolt://localhost:7687`      |

## Default Credentials

| Service   | Username / Email       | Password   |
|-----------|----------------------|------------|
| Web Login | `demo@medbed.local`  | `demo123`  |
| PostgreSQL | `medbed`            | `medbed`   |
| Neo4j     | `neo4j`              | `medbed123`|

---

## Starting Services

### Core stack (no ML)

```bash
docker compose up -d
# or
make up
```

Starts: PostgreSQL, Redis, Neo4j, API, Celery worker, Web.
Embeddings will use **mock fallback** (deterministic hash-based vectors).

### Full stack (with ML service)

```bash
docker compose --profile ml up -d
# or
make up-full
```

Adds the ML service (BioClinical-ModernBERT). First start downloads the ~600MB model on first `/embed` request.

### Warm up the ML model

```bash
make warm-model
```

Sends a test embedding request to trigger model download/load. Takes ~15-30s on first run (model download), ~1s after.

---

## Restarting Services

### Web only (fixes stale `.next` cache / auth errors)

```bash
docker compose stop web && docker compose rm -f web && docker compose up -d web
```

> **Why `rm -f`?** The web container uses an anonymous Docker volume for `/app/.next`. A simple `restart` keeps the old (possibly corrupted) build cache. Removing and recreating the container gives it a fresh volume.

### API + Celery worker (after Python code changes)

```bash
docker compose restart api celery-worker
```

The API and worker mount `./api` as a volume, so code changes are picked up on restart without rebuilding.

### ML service

```bash
docker compose --profile ml restart ml
```

### Full restart (all services)

```bash
docker compose down && docker compose up -d
```

### Full restart including ML

```bash
docker compose down && docker compose --profile ml up -d
```

### Nuclear reset (destroys all data)

```bash
docker compose down -v
# or
make clean
```

This removes all Docker volumes (database, Redis, uploads, model cache). You'll need to re-run migrations and seed data after.

---

## Rebuilding Images

After changing `Dockerfile`, `requirements.txt`, or `package.json`:

```bash
# Rebuild API image
docker compose build api

# Rebuild web image
docker compose build web

# Rebuild ML image
docker compose --profile ml build ml

# Rebuild all
docker compose build
```

After rebuilding, restart the affected service (see above).

---

## Health Checks

### All services

```bash
curl -s http://localhost:8010/health | python3 -m json.tool
```

Expected output:
```json
{
    "status": "ok",
    "services": {
        "db": "ok",
        "redis": "ok",
        "ml": "ok (model loaded)",
        "neo4j": "ok"
    }
}
```

### ML service only

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
# or
make ml-health
```

---

## Database

### Open psql shell

```bash
docker compose exec db psql -U medbed -d medbed
# or
make db-shell
```

### Connect from host (e.g. pgAdmin, DBeaver)

```
Host: localhost
Port: 5435
Database: medbed
User: medbed
Password: medbed
```

### Run migrations

```bash
docker compose exec api alembic upgrade head
# or
make migrate
```

### Create a new migration

```bash
make migration msg="describe_your_change"
```

### Seed demo data

```bash
docker compose exec api python -m app.seed
# or
make seed
```

---

## Logs

```bash
# All services
docker compose logs -f
# or
make logs

# Specific service
docker compose logs -f api
docker compose logs -f celery-worker
docker compose logs -f web

# ML service
docker compose --profile ml logs -f ml
# or
make ml-logs
```

---

## E2E Pipeline Test

Runs the full pipeline: login, upload PDF, trigger analysis, poll for completion, verify results.

```bash
bash scripts/test_e2e_pipeline.sh
```

Expected output ends with:
```
=== Test Summary ===
  Entries parsed:     434
  Embedding source:   real
  Clusters found:     15
  UMAP coords:        yes
  Recovery plan:      yes

✓ E2E pipeline test PASSED
```

---

## Makefile Targets

| Target       | Description                                      |
|--------------|--------------------------------------------------|
| `make up`    | Start core stack (no ML)                         |
| `make down`  | Stop all services                                |
| `make up-full` | Start all services including ML                |
| `make logs`  | Tail logs for all services                       |
| `make ml-logs` | Tail ML service logs                           |
| `make db-shell` | Open psql shell                               |
| `make migrate` | Run Alembic migrations                         |
| `make migration msg="..."` | Generate new Alembic migration    |
| `make seed`  | Seed demo data                                   |
| `make test-api` | Run API tests (pytest)                        |
| `make test-web` | Run web tests                                 |
| `make lint`  | Run linters (ruff + eslint)                      |
| `make clean` | Stop services and destroy all volumes            |
| `make warm-model` | Trigger ML model download/load              |
| `make ml-health` | Check ML service health                      |

---

## Troubleshooting

### Auth errors / 401 on login

The web container's `.next` build cache is corrupted. Fix:
```bash
docker compose stop web && docker compose rm -f web && docker compose up -d web
```

### "Unknown Patient" after upload

If patient name shows as "Unknown Patient", the PDF parser couldn't extract demographics. This was fixed in Phase 2 — ensure the API container has the latest code:
```bash
docker compose restart api
```

### ML service won't start / import error

Rebuild the ML image to pick up code changes:
```bash
docker compose --profile ml build ml
docker compose --profile ml up -d ml
```

### Port conflicts

If ports 3010, 8010, 5435, etc. are already in use, either stop the conflicting process or edit the port mappings in `docker-compose.yml` under `ports:`.

### Celery tasks stuck / not processing

```bash
docker compose restart celery-worker
```

Check worker logs:
```bash
docker compose logs -f celery-worker
```
