# Claude Code Prompt: MedBed Insight Analytics Platform — E2E Cloud Application

## Role & Context

You are building a full-stack, cloud-hosted medical analytics platform called **MedBed Insight**. This application ingests frequency-based body scan reports from a Tesla Med Bed device, runs them through an NLP-powered pattern recognition pipeline, and presents diagnostic insights with recovery plan recommendations through an interactive dashboard.

---

## System Architecture Overview

Build a **5-layer architecture** deployed on AWS (or GCP alternative noted where applicable):

```
Layer 1: Data Ingestion API        → FastAPI + Celery workers
Layer 2: NLP Embedding Engine      → BioClinical ModernBERT (HuggingFace)
Layer 3: Clinical Knowledge Graph  → Neo4j Aura + KEGG/DisGeNET/HPO/SNOMED
Layer 4: Pattern Recognition       → Clustering, trend detection, risk scoring
Layer 5: Dashboard + Recovery Plan → Next.js 14 + D3.js + Recharts
```

---

## Layer 1 — Data Ingestion & Normalization API

### Report Parser

Build a FastAPI service that accepts MedBed scan reports. Each report contains rows with:
- **Condition name** (e.g., "Chronic Reflux-Gastritis", "Cholestatic Hepatosis")
- **Anatomical location** (e.g., "Transition of Esophagus to Stomach", "Interlobular Bile Duct")
- **Numerical score** (float between 0.0 and 1.0, representing a frequency deviation metric)
- **Green/Red ratio** (a visual bar indicator — parse as a percentage split)
- **Organ system category** (e.g., "02 Digestive System")
- **Timestamp** of the scan session

### Input Formats to Support
1. **PDF upload** — OCR with `pytesseract` + `pdf2image`, then structured extraction
2. **CSV/JSON upload** — direct structured parse
3. **Manual entry** — form-based input through the dashboard
4. **Image upload** — screenshot of report (use a vision model or OCR pipeline)

### Normalization Pipeline
For each parsed condition, run:
1. **ICD-10 mapping** — use the UMLS REST API (NLM account required) to map condition names to ICD-10 codes
2. **SNOMED CT mapping** — map to SNOMED concept IDs for granular clinical linking
3. **FMA mapping** — map anatomical location strings to Foundational Model of Anatomy identifiers
4. **Score normalization** — standardize scores to a 0–1 range with z-score normalization across the report

### Data Models (PostgreSQL via SQLAlchemy)

```python
class Patient(Base):
    id: UUID
    name: str (encrypted at rest)
    created_at: datetime
    sessions: relationship -> ScanSession[]

class ScanSession(Base):
    id: UUID
    patient_id: FK -> Patient
    scan_date: datetime
    raw_report_url: str  # S3 presigned URL to original upload
    organ_system: str
    entries: relationship -> ScanEntry[]

class ScanEntry(Base):
    id: UUID
    session_id: FK -> ScanSession
    condition_name: str
    condition_icd10: str
    condition_snomed: str
    anatomical_location: str
    anatomical_fma_id: str
    score: float
    green_ratio: float
    red_ratio: float
    embedding_vector: Vector(768)  # pgvector column
    cluster_id: int (nullable)
    risk_tier: str (nullable)  # "low", "moderate", "high", "critical"
```

### API Endpoints

```
POST   /api/v1/reports/upload          — Upload a new scan report (PDF/CSV/image)
GET    /api/v1/reports/{session_id}    — Get parsed report with all entries
GET    /api/v1/patients/{patient_id}/history  — All sessions for a patient
POST   /api/v1/reports/{session_id}/analyze   — Trigger full NLP + KG analysis pipeline
GET    /api/v1/reports/{session_id}/insights  — Get generated insights + recovery plan
POST   /api/v1/reports/compare         — Compare two sessions side-by-side
```

---

## Layer 2 — NLP Embedding Engine (BioClinical ModernBERT)

### Model Selection

Use **BioClinical ModernBERT** as the primary encoder. This is a 2025 state-of-the-art model that replaces the older BioBERT/ClinicalBERT approach:

- **Base model**: `thomas-sounack/BioClinical-ModernBERT-base` (150M params)
- **Large model**: `thomas-sounack/BioClinical-ModernBERT-large` (396M params) — use this for production
- **Embedding-optimized variant**: `lokeshch19/ModernPubMedBERT` — fine-tuned for sentence similarity, use for the clustering/similarity layer

### Why BioClinical ModernBERT over BioBERT/ClinicalBERT
- **8,192 token context window** (vs 512) — can embed an entire report in one pass
- **53.5B training tokens** from 20 diverse clinical datasets (vs single-source MIMIC-III)
- **No catastrophic forgetting** — retains biomedical knowledge after clinical specialization
- **Flash Attention 2 support** — fastest clinical encoder available
- **SOTA on ChemProt (90.8% F1), Phenotype (60.8% F1), DEID, and NER tasks**
- **MIT licensed** — fully open for commercial and research use

### Embedding Pipeline

```python
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import torch

# Primary encoder — full contextual embeddings
tokenizer = AutoTokenizer.from_pretrained("thomas-sounack/BioClinical-ModernBERT-large")
encoder = AutoModel.from_pretrained(
    "thomas-sounack/BioClinical-ModernBERT-large",
    torch_dtype=torch.bfloat16
)

# Similarity-optimized model — for clustering and nearest-neighbor lookups
similarity_model = SentenceTransformer("lokeshch19/ModernPubMedBERT")

def embed_entry(condition: str, anatomy: str, score: float) -> np.ndarray:
    """Generate a 768-dim embedding for a single report entry."""
    text = f"{condition}, located at {anatomy}, deviation score {score:.3f}"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = encoder(**inputs)
    return outputs.last_hidden_state[:, 0, :].squeeze().numpy()

def embed_full_report(entries: list[dict]) -> np.ndarray:
    """Embed entire report as single contextual unit using 8K context window."""
    report_text = " [SEP] ".join(
        f"{e['condition']}, {e['anatomy']}, score: {e['score']:.3f}"
        for e in entries
    )
    inputs = tokenizer(report_text, return_tensors="pt", truncation=True, max_length=8192)
    with torch.no_grad():
        outputs = encoder(**inputs)
    return outputs.last_hidden_state[:, 0, :].squeeze().numpy()

def compute_similarity_matrix(entries: list[dict]) -> np.ndarray:
    """Use the similarity-optimized model for clustering."""
    texts = [f"{e['condition']}, {e['anatomy']}" for e in entries]
    embeddings = similarity_model.encode(texts)
    from sklearn.metrics.pairwise import cosine_similarity
    return cosine_similarity(embeddings)
```

### Clustering Pipeline
- Use **HDBSCAN** for density-based clustering of condition embeddings
- Use **UMAP** for dimensionality reduction (768 → 2D for visualization, 768 → 50D for clustering input)
- Store cluster assignments back in `ScanEntry.cluster_id`
- Name clusters automatically by finding the most representative condition per cluster

### Model Serving
- Deploy the model behind a **dedicated GPU inference service** (AWS SageMaker endpoint, or a self-hosted container on an EC2 g5.xlarge with NVIDIA A10G)
- Use **batched inference** — process all entries in a report together
- Cache embeddings in **pgvector** (PostgreSQL extension) for fast retrieval and similarity search
- Set up a **model registry** using MLflow to track model versions and performance

---

## Layer 3 — Clinical Knowledge Graph

### Graph Database: Neo4j Aura (managed) or self-hosted Neo4j 5+

### Schema

```cypher
// Node types
(:Disease {name, icd10, snomed_id, description})
(:AnatomicalStructure {name, fma_id, organ_system, parent_structure})
(:BiologicalPathway {name, kegg_id, pathway_type, description})
(:Gene {symbol, name, ncbi_id, ensembl_id})
(:Phenotype {name, hpo_id, description})
(:DrugTarget {name, drugbank_id, mechanism, drug_class})
(:NutritionalFactor {name, type, description})  // vitamins, minerals, compounds
(:LifestyleIntervention {name, category, evidence_level})

// Relationship types
(:Disease)-[:AFFECTS]->(:AnatomicalStructure)
(:Disease)-[:PART_OF_PATHWAY]->(:BiologicalPathway)
(:Disease)-[:ASSOCIATED_GENE]->(:Gene)
(:Disease)-[:HAS_PHENOTYPE]->(:Phenotype)
(:Disease)-[:TREATED_BY]->(:DrugTarget)
(:Disease)-[:SUPPORTED_BY]->(:NutritionalFactor)
(:Disease)-[:RESPONDS_TO]->(:LifestyleIntervention)
(:Disease)-[:COMORBID_WITH]->(:Disease)
(:AnatomicalStructure)-[:PART_OF]->(:AnatomicalStructure)
(:BiologicalPathway)-[:INVOLVES_GENE]->(:Gene)
(:Gene)-[:TARGETED_BY]->(:DrugTarget)
```

### Data Sources to Ingest

| Source | What It Provides | Format | URL |
|--------|-----------------|--------|-----|
| KEGG Disease | Disease-to-pathway mappings | REST API | https://rest.kegg.jp |
| KEGG Pathway | Metabolic/signaling pathway details | REST API | https://rest.kegg.jp |
| DisGeNET | Disease-gene associations with evidence scores | TSV download | https://www.disgenet.org |
| HPO | Disease-phenotype mappings | OBO/JSON | https://hpo.jax.org |
| DrugBank (open) | Drug-target-disease relationships | XML | https://go.drugbank.com |
| SNOMED CT | Clinical terminology graph | RF2 release | https://www.nlm.nih.gov/snomed |
| UMLS Metathesaurus | Cross-terminology mappings | RRF files | https://www.nlm.nih.gov/research/umls |
| Uberon | Cross-species anatomy ontology | OWL/OBO | http://uberon.org |

### Reasoning Queries

Build the following query templates for the insight engine:

```cypher
// 1. Find shared pathways between co-occurring conditions
MATCH (d1:Disease {icd10: $icd1})-[:PART_OF_PATHWAY]->(p:Pathway)<-[:PART_OF_PATHWAY]-(d2:Disease {icd10: $icd2})
RETURN p.name, p.kegg_id, d1.name, d2.name

// 2. Get the full context for a condition
MATCH (d:Disease {icd10: $icd})-[r]->(target)
RETURN type(r) AS relationship, labels(target)[0] AS target_type, target.name AS target_name

// 3. Find all nutritional/lifestyle interventions for a cluster of conditions
MATCH (d:Disease)-[:SUPPORTED_BY]->(n:NutritionalFactor)
WHERE d.icd10 IN $icd_list
RETURN n.name, n.type, count(d) AS conditions_supported, collect(d.name) AS conditions

// 4. Identify systemic patterns (conditions sharing >2 pathways)
MATCH (d1:Disease)-[:PART_OF_PATHWAY]->(p:Pathway)<-[:PART_OF_PATHWAY]-(d2:Disease)
WHERE d1.icd10 IN $report_icds AND d2.icd10 IN $report_icds AND d1 <> d2
WITH d1, d2, count(p) AS shared_pathways, collect(p.name) AS pathway_names
WHERE shared_pathways >= 2
RETURN d1.name, d2.name, shared_pathways, pathway_names
ORDER BY shared_pathways DESC

// 5. Recovery plan: aggregate interventions ranked by evidence and coverage
MATCH (d:Disease)-[:RESPONDS_TO]->(li:LifestyleIntervention)
WHERE d.icd10 IN $icd_list
RETURN li.name, li.category, li.evidence_level,
       count(d) AS conditions_addressed, collect(d.name) AS targets
ORDER BY conditions_addressed DESC, li.evidence_level DESC
```

---

## Layer 4 — Pattern Recognition & Diagnostic Insight Engine

### 4A. Correlation Detector
- Takes embedding clusters (from Layer 2) and knowledge graph paths (from Layer 3)
- Computes a **dual-signal confidence score**: conditions that are BOTH semantically similar (cosine > 0.7) AND graph-connected (shared pathway count ≥ 2) receive the highest pattern confidence
- Output: ranked list of condition clusters with confidence scores and pathway explanations

### 4B. Temporal Trend Analyzer
- For patients with multiple scan sessions, compute per-condition score trajectories
- Use **simple linear regression** for trend direction (improving / worsening / stable)
- Use **change point detection** (PELT algorithm via `ruptures` library) to flag sudden shifts
- Store trends in a time-series table (or use TimescaleDB hypertable)

```python
class ConditionTrend(Base):
    id: UUID
    patient_id: FK -> Patient
    condition_icd10: str
    condition_name: str
    trend_direction: str  # "improving", "worsening", "stable", "volatile"
    trend_slope: float
    sessions_analyzed: int
    last_score: float
    first_score: float
    change_points: JSON  # list of {session_id, date, old_score, new_score}
```

### 4C. Risk Stratifier
Compute a composite risk score per organ system:

```python
def compute_organ_risk(entries: list[ScanEntry], trends: list[ConditionTrend]) -> dict:
    """
    Weighted scoring:
    - 40% current score severity (average score in organ system)
    - 25% trend direction (worsening = higher risk)
    - 20% cluster density (more correlated conditions = systemic issue)
    - 15% knowledge graph pathway load (conditions sharing critical pathways)
    """
    # Return: {"organ_system": str, "risk_tier": str, "risk_score": float,
    #          "contributing_factors": list, "recommended_focus": str}
```

Risk tiers: `low` (0–0.25), `moderate` (0.25–0.5), `high` (0.5–0.75), `critical` (0.75–1.0)

### 4D. Recovery Plan Generator

This is the key diagnostic output. For each analysis, generate a structured recovery plan:

```python
class RecoveryPlan(Base):
    id: UUID
    session_id: FK -> ScanSession
    patient_id: FK -> Patient
    generated_at: datetime
    summary: Text  # 2-3 paragraph plain-language overview
    organ_system_breakdown: JSON  # per-system analysis
    priority_conditions: JSON  # top 5 conditions ranked by risk
    recommended_interventions: JSON  # structured list (see below)
    lifestyle_recommendations: JSON
    nutritional_recommendations: JSON
    monitoring_plan: JSON  # what to watch for in next scan
    disclaimer: str  # always present

# Intervention structure:
{
    "intervention": str,
    "category": "nutritional" | "lifestyle" | "monitoring" | "specialist_referral",
    "targets": [condition_names],
    "evidence_level": "strong" | "moderate" | "emerging",
    "priority": "immediate" | "short_term" | "ongoing",
    "reasoning": str  # knowledge graph path explaining why
}
```

The recovery plan is generated by:
1. Querying the knowledge graph for all interventions connected to the patient's conditions
2. Ranking interventions by: (a) how many conditions they address, (b) evidence level, (c) risk tier of the target conditions
3. Grouping into nutritional, lifestyle, monitoring, and referral categories
4. Using an LLM (Claude API via Anthropic SDK) to generate the plain-language summary paragraph, synthesizing the structured data into readable prose

---

## Layer 5 — Dashboard (Next.js 14 + React) using Anthropic frontend skills from https://skills.sh/anthropics/skills/frontend-design

### Tech Stack
- **Framework**: Next.js 14 (App Router) with TypeScript
- **Styling**: Tailwind CSS + shadcn/ui component library
- **Charts**: Recharts for standard charts, D3.js for the body map and knowledge graph explorer
- **State**: Zustand for client state, TanStack Query for server state
- **Auth**: NextAuth.js with credential provider (email/password) + optional OAuth
- **Real-time**: Server-Sent Events for analysis progress updates

### Dashboard Pages

#### 1. `/dashboard` — Overview
- **Patient selector** dropdown at top
- **Organ system risk heatmap** — body silhouette SVG with colored overlays per organ system (green/yellow/orange/red based on risk tier)
- **Latest scan summary** — metric cards showing: total conditions flagged, highest risk organ system, trend direction since last scan, overall wellness score
- **Alert banner** — if any condition has moved to "critical" tier or trend is sharply worsening
- **Quick actions** — "Upload New Scan", "View Recovery Plan", "Compare Sessions"

#### 2. `/dashboard/report/{session_id}` — Single Report View
- **Condition table** — sortable/filterable table of all entries with: condition name, anatomy, score, ICD-10 code, risk tier badge, trend arrow (if prior sessions exist)
- **Cluster visualization** — UMAP 2D scatter plot (D3.js) showing condition embeddings colored by cluster, with hover tooltips showing condition details
- **Score distribution** — histogram of all scores in the report, with organ system breakdown
- **Green/Red ratio chart** — stacked bar chart matching the original report format

#### 3. `/dashboard/trends/{patient_id}` — Temporal Trend View
- **Sparkline grid** — one sparkline per condition showing score over time across all sessions
- **Trend summary cards** — "Improving" (green), "Stable" (blue), "Worsening" (orange), "Critical" (red) with counts
- **Session comparison slider** — pick any two sessions and see a side-by-side diff with delta scores
- **Change point timeline** — horizontal timeline marking significant score shifts with annotations

#### 4. `/dashboard/insights/{session_id}` — Diagnostic Insights
- **Pattern cards** — each detected pattern (cluster of correlated conditions) shown as a card with:
  - Cluster name and member conditions
  - Shared biological pathways (from knowledge graph)
  - Confidence score (dual-signal)
  - "Explore in Knowledge Graph" button
- **Knowledge graph explorer** — interactive force-directed graph (D3.js or react-force-graph) showing the patient's conditions as central nodes connected to pathways, genes, and interventions. Click any node to expand its connections.
- **Root cause hypotheses** — ranked list of potential underlying patterns based on pathway convergence

#### 5. `/dashboard/recovery/{session_id}` — Recovery Plan
- **Summary section** — LLM-generated plain-language overview (2-3 paragraphs)
- **Priority conditions table** — top 5 conditions by risk, each with trend, current score, and recommended focus
- **Intervention timeline** — visual Gantt-like chart showing immediate / short-term / ongoing interventions
- **Categorized recommendations**:
  - **Nutritional**: vitamins, minerals, dietary changes with knowledge graph reasoning
  - **Lifestyle**: exercise, stress management, sleep, with evidence levels
  - **Monitoring**: what metrics to watch, suggested re-scan interval
  - **Specialist considerations**: when patterns suggest professional consultation would be valuable
- **Progress tracker** — patient can check off completed interventions, track adherence
- **Export options** — PDF report generation, printable summary

#### 6. `/dashboard/compare` — Session Comparison
- **Side-by-side tables** with delta highlighting (green for improved scores, red for worsened)
- **Radar chart** — organ system risk scores overlaid for both sessions
- **New/Resolved conditions** — what appeared or disappeared between scans

### Design Requirements
- **Responsive** — works on desktop and tablet (primary use: clinical setting with large screen)
- **Dark/light mode** — toggle in header, persist preference
- **Accessibility** — WCAG 2.1 AA compliant, screen reader support for all charts (aria labels + data tables)
- **Print-friendly** — recovery plan page has a print stylesheet
- **Loading states** — skeleton loaders on all data-dependent components; analysis pipeline shows a step-by-step progress indicator via SSE

---

## Development Phases

### Phase 1 (Weeks 1–3): Foundation
- [ ] Set up monorepo structure: `/api` (FastAPI), `/web` (Next.js), `/infra` (Terraform/CDK), `/ml` (model serving)
- [ ] PostgreSQL schema + migrations (Alembic)
- [ ] FastAPI skeleton with health checks, CORS, auth middleware
- [ ] Report upload endpoint (PDF + CSV parsing)
- [ ] Next.js app shell with auth, layout, patient selector
- [ ] Docker Compose for local development (Postgres, Redis, Neo4j)

### Phase 2 (Weeks 3–6): NLP Pipeline
- [ ] BioClinical ModernBERT integration (local first, then SageMaker)
- [ ] Embedding generation + pgvector storage
- [ ] HDBSCAN clustering + UMAP visualization data
- [ ] ICD-10 / SNOMED / FMA normalization pipeline
- [ ] Celery task chain: upload → parse → normalize → embed → cluster

### Phase 3 (Weeks 5–9): Knowledge Graph
- [ ] Neo4j schema + seed data from KEGG, DisGeNET, HPO
- [ ] Graph query templates (shared pathways, interventions, systemic patterns)
- [ ] Reasoning engine: dual-signal confidence scoring
- [ ] API endpoints for graph exploration data

### Phase 4 (Weeks 8–12): Insights & Recovery
- [ ] Risk stratification engine
- [ ] Temporal trend analyzer (requires test data with multiple sessions)
- [ ] Recovery plan generator (structured data + LLM summary via Anthropic API)
- [ ] Full insights API with caching

### Phase 5 (Weeks 10–14): Dashboard
- [ ] Report view with condition table + cluster viz
- [ ] Body map SVG with organ system risk overlay
- [ ] Trend sparklines and session comparison
- [ ] Knowledge graph explorer (D3 force-directed)
- [ ] Recovery plan page with export to PDF
- [ ] Progress tracker for interventions

### Phase 6 (Weeks 14–16): Production & Polish

---

## File Structure

```
medbed-insight/
├── api/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── config.py                # Environment-based settings
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── patient.py
│   │   │   ├── session.py
│   │   │   ├── entry.py
│   │   │   ├── trend.py
│   │   │   └── recovery.py
│   │   ├── routers/                 # API route handlers
│   │   │   ├── reports.py
│   │   │   ├── patients.py
│   │   │   ├── insights.py
│   │   │   ├── recovery.py
│   │   │   └── compare.py
│   │   ├── services/                # Business logic
│   │   │   ├── parser.py            # PDF/CSV/image parsing
│   │   │   ├── normalizer.py        # ICD-10/SNOMED/FMA mapping
│   │   │   ├── embedder.py          # BioClinical ModernBERT pipeline
│   │   │   ├── clusterer.py         # HDBSCAN + UMAP
│   │   │   ├── graph_client.py      # Neo4j query interface
│   │   │   ├── trend_analyzer.py    # Temporal analysis
│   │   │   ├── risk_engine.py       # Risk stratification
│   │   │   └── recovery_planner.py  # Recovery plan generator
│   │   ├── tasks/                   # Celery async tasks
│   │   │   ├── analyze.py           # Full analysis pipeline task chain
│   │   │   └── export.py            # PDF generation
│   │   └── utils/
│   │       ├── encryption.py        # PHI encryption helpers
│   │       └── umls_client.py       # UMLS REST API wrapper
│   ├── migrations/                  # Alembic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── web/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── dashboard/
│   │   │   ├── page.tsx             # Overview
│   │   │   ├── report/[id]/page.tsx # Single report
│   │   │   ├── trends/[id]/page.tsx # Temporal trends
│   │   │   ├── insights/[id]/page.tsx
│   │   │   ├── recovery/[id]/page.tsx
│   │   │   └── compare/page.tsx
│   │   └── api/auth/[...nextauth]/route.ts
│   ├── components/
│   │   ├── body-map/                # Interactive SVG body silhouette
│   │   ├── cluster-viz/             # UMAP scatter plot (D3)
│   │   ├── knowledge-graph/         # Force-directed graph explorer
│   │   ├── trend-sparklines/        # Recharts sparkline grid
│   │   ├── risk-cards/              # Organ system risk display
│   │   ├── recovery-plan/           # Recovery plan renderer
│   │   └── report-table/            # Sortable condition table
│   ├── lib/
│   │   ├── api-client.ts            # Typed API client
│   │   └── stores/                  # Zustand stores
│   ├── Dockerfile
│   └── package.json
├── ml/
│   ├── serve/
│   │   ├── handler.py               # SageMaker inference handler
│   │   └── requirements.txt
│   ├── notebooks/                   # Exploration and evaluation
│   └── scripts/
│       └── seed_knowledge_graph.py  # Neo4j data ingestion scripts
├── infra/
│   ├── main.tf (or cdk/)
│   ├── modules/
│   │   ├── vpc/
│   │   ├── ecs/
│   │   ├── rds/
│   │   ├── sagemaker/
│   │   └── s3/
│   └── environments/
│       ├── dev.tfvars
│       ├── staging.tfvars
│       └── prod.tfvars
├── docker-compose.yml               # Local development
├── Makefile                         # Common commands
└── README.md
```

---

## Key Technical Decisions

1. **BioClinical ModernBERT large** over BioBERT — 8K context, SOTA benchmarks, no forgetting, Flash Attention 2
2. **pgvector** over Pinecone/Weaviate — keeps embeddings co-located with relational data, simpler architecture
3. **Neo4j** over Amazon Neptune — richer Cypher query language, better ecosystem for biomedical ontologies
4. **Celery** over AWS Step Functions — more portable, easier local development, sufficient for this pipeline complexity
5. **Next.js** over pure React SPA — SSR for initial load performance, API routes for BFF pattern, built-in image optimization
6. **ModernPubMedBERT** as the similarity model — purpose-built for medical concept similarity, better discrimination than generic embeddings

---

## Constraints & Non-Negotiables

1. **Every page must show the medical disclaimer** — this is not a diagnostic tool, it's an analytical exploration platform
2. **Patient data encryption** — names and identifiers encrypted at rest and in transit, never logged in plaintext
3. **Recovery plans always include** the recommendation to consult a qualified healthcare provider
4. **No hard medical claims** — all insights framed as "patterns suggest", "data indicates", "may be associated with"
5. **Audit trail** — every analysis, plan generation, and data access logged with timestamp and user ID
6. **Graceful degradation** — if the ML pipeline fails, the dashboard still shows raw parsed data; if Neo4j is down, insights page shows "Knowledge graph temporarily unavailable" with a retry button

---

Begin by scaffolding the monorepo, Docker Compose setup, and the FastAPI skeleton with the PostgreSQL schema. Then proceed phase by phase. Ask clarifying questions if any architectural decision needs refinement before implementation.