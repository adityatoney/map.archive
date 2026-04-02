# Agentic Clinical Analysis — End-to-End Design

## Context

The MedBed Insight platform has a full NLP pipeline (PDF → parse → normalize → embed → cluster → trend → composite risk → KG query → recovery plan) with a Neo4j knowledge graph (493 nodes, 1354 relationships). The recovery plan currently provides structured data (priority conditions, interventions, monitoring) but lacks **deep diagnostic reasoning** — identifying systemic cascade patterns like "gut dysfunction → nutrient malabsorption → liver stress → blood quality → nervous system effects."

The user wants to leverage Claude to produce **agentic clinical insights**: root cause identification, organ-to-organ cascade chains, and pattern analysis grounded in the knowledge graph data. This is distinct from the existing recovery plan summary (which is a brief narrative). This is a full clinical analysis section with structured outputs.

A `clinical_analyzer.py` service was already created (prematurely) and provides a solid foundation. This plan integrates it into the pipeline, persists results, exposes an API, and builds the frontend.

---

## Architecture Overview

```
Pipeline (Celery task):
  ... → cluster → trends → composite risk → KG queries → recovery plan
                                                       → CLINICAL ANALYSIS (new Step 6b)
                                                         ↓
                                                    ClinicalAnalysis DB record

Frontend:
  /dashboard/clinical-analysis/[id] ← GET /api/v1/clinical/{session_id}
```

**Data flow into Claude:**
- All scan entries with scores, organ systems, ICD-10 codes
- Composite organ risk scores with 4-component breakdown
- Knowledge graph: shared pathways between condition pairs
- Knowledge graph: per-condition connectivity (pathways, comorbidities, interventions)
- Knowledge graph: nutritional + lifestyle interventions with evidence
- Temporal trends (improving/worsening/stable/volatile)
- Priority conditions (deduplicated, KG-weighted)

**Structured output from Claude:**
- `systemic_analysis` — 2-3 paragraph narrative with cascade reasoning
- `root_systems` — identified root organ systems driving downstream issues
- `cascade_chains` — organ → organ → organ chains with mechanisms and supporting pathways
- `key_patterns` — grouped conditions sharing biological pathways
- `actionable_insights` — prioritized focus areas with KG evidence

---

## Wave 1: Backend — Database Model & Migration

### 1a. New model: `api/app/models/clinical_analysis.py`

```python
class ClinicalAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clinical_analyses"

    session_id: UUID FK → scan_sessions.id (unique)
    patient_id: UUID FK → patients.id (indexed)
    generated_at: DateTime (server_default=now)

    # LLM-generated content (JSON columns)
    systemic_analysis: Text (nullable)        # narrative
    root_systems: JSON (nullable)             # list of root system dicts
    cascade_chains: JSON (nullable)           # list of cascade chain dicts
    key_patterns: JSON (nullable)             # list of pattern dicts
    actionable_insights: JSON (nullable)      # list of insight dicts

    # Metadata
    analysis_source: String  # "llm" or "template"
    model_used: String (nullable)  # e.g. "claude-sonnet-4-20250514"
    context_token_count: Integer (nullable)  # track prompt size

    disclaimer: Text (not null)
```

**Why a separate table (not a column on RecoveryPlan)?**
- Separation of concerns: recovery plan = structured treatment data; clinical analysis = diagnostic reasoning
- Independent lifecycle: can regenerate one without the other
- Different display pages in the frontend
- Cleaner API response types

### 1b. Alembic migration

Standard migration: `alembic revision --autogenerate -m "add clinical_analyses table"`

### 1c. Add relationship to ScanSession model

In `api/app/models/session.py`:
```python
clinical_analysis = relationship("ClinicalAnalysis", back_populates="session", uselist=False)
```

---

## Wave 2: Backend — LLM Integration (Anthropic SDK)

### 2a. Switch from `claude-agent-sdk` to `anthropic` Python SDK

The existing `clinical_analyzer.py` uses `claude_agent_sdk.query()` which spawns a subprocess. For a single structured LLM call (no tools needed), the **Anthropic Python SDK** is simpler, more reliable, and doesn't require Claude Code CLI in the Docker container.

**Update `api/requirements.txt`**: Add `anthropic` (if not present), remove `claude-agent-sdk` dependency for this use case.

**Update `api/app/config.py`**: Ensure `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` settings exist.

### 2b. Refactor `api/app/services/clinical_analyzer.py`

**Keep existing**: `_build_analysis_context()` (lines 62-247) — excellent context builder, no changes needed.

**Keep existing**: `_analyze_template()` (lines 363-494) — solid fallback, no changes needed.

**Replace `_analyze_with_llm()`** with Anthropic SDK call:

```python
async def _analyze_with_llm(self, context: str) -> dict[str, Any] | None:
    try:
        import anthropic
        settings = get_settings()

        if not settings.ANTHROPIC_API_KEY:
            logger.info("No ANTHROPIC_API_KEY; using template analysis")
            return None

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,  # existing system prompt (lines 258-311)
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text
        # ... existing JSON parsing logic ...
```

**Key benefits over claude-agent-sdk:**
- No subprocess spawning — pure async HTTP call
- Works in Docker without Claude Code CLI
- Standard API key auth (no OAuth/Max subscription required)
- Predictable latency (~5-15 seconds)

**Return metadata** for the DB record:
```python
return {
    **parsed,
    "_meta": {
        "source": "llm",
        "model": settings.ANTHROPIC_MODEL,
        "input_tokens": response.usage.input_tokens,
    }
}
```

### 2c. Update `analyze()` method signature

Add return of metadata so the pipeline can store `analysis_source` and `model_used`:

```python
async def analyze(self, ...) -> dict[str, Any]:
    # Returns: systemic_analysis, root_systems, cascade_chains,
    #          key_patterns, actionable_insights, disclaimer,
    #          _meta: {source, model, input_tokens}
```

---

## Wave 3: Backend — Pipeline Integration

### 3a. Wire into `api/app/tasks/analyze.py`

Add **Step 6b** after recovery plan generation (Step 6), before status update (Step 7):

```python
# Step 6b: Clinical analysis (LLM-powered)
from app.services.clinical_analyzer import ClinicalAnalyzerService
from app.models.clinical_analysis import ClinicalAnalysis

analyzer = ClinicalAnalyzerService()
clinical_result = await analyzer.analyze(
    entries=entry_dicts,
    organ_risks=organ_risks,
    graph_interventions=graph_interventions or None,
    systemic_patterns=systemic,        # already queried in Step 5a
    graph_connectivity=graph_connectivity or None,
    trends=trends,
    priority_conditions=plan_data["priority_conditions"],
)

# Delete existing clinical analysis if re-analyzing
await db.execute(
    delete(ClinicalAnalysis).where(ClinicalAnalysis.session_id == session.id)
)

# Save clinical analysis
meta = clinical_result.pop("_meta", {})
db.add(ClinicalAnalysis(
    session_id=session.id,
    patient_id=session.patient_id,
    systemic_analysis=clinical_result.get("systemic_analysis"),
    root_systems=clinical_result.get("root_systems"),
    cascade_chains=clinical_result.get("cascade_chains"),
    key_patterns=clinical_result.get("key_patterns"),
    actionable_insights=clinical_result.get("actionable_insights"),
    analysis_source=meta.get("source", "template"),
    model_used=meta.get("model"),
    context_token_count=meta.get("input_tokens"),
    disclaimer=clinical_result["disclaimer"],
))
```

**Note**: The `systemic` variable (shared pathways) is already computed in Step 5a. We need to capture it in a variable that persists to Step 6b (currently it's inside a try block — move the variable declaration before the try).

### 3b. Handle the `systemic_patterns` data

Currently `systemic = await graph_client.find_systemic_patterns(icd_list)` is computed inside a nested try block in Step 5a. Promote the `systemic` variable to the outer scope so it's available for Step 6b:

```python
systemic_patterns: list[dict] = []  # declare before try block
# ... inside try: systemic_patterns = await graph_client.find_systemic_patterns(...)
```

### 3c. Delete cascade for clinical_analyses

Update the report deletion endpoint (`api/app/routers/reports.py`) to also delete clinical analysis:
```python
from app.models.clinical_analysis import ClinicalAnalysis
await db.execute(sa_delete(ClinicalAnalysis).where(ClinicalAnalysis.session_id == session.id))
```

---

## Wave 4: Backend — API Endpoint

### 4a. New router: `api/app/routers/clinical.py`

```python
router = APIRouter()

class RootSystemResponse(BaseModel):
    organ_system: str
    confidence: str  # high/medium/low
    reasoning: str
    downstream_effects: list[str]

class CascadeChainResponse(BaseModel):
    chain: list[str]
    mechanism: str
    supporting_pathways: list[str]
    key_conditions: list[str]

class KeyPatternResponse(BaseModel):
    pattern_name: str
    conditions_involved: list[str]
    shared_pathways: list[str]
    clinical_significance: str
    severity: str  # critical/high/moderate/low

class ActionableInsightResponse(BaseModel):
    priority: int
    focus_area: str
    reasoning: str
    supported_by: str

class ClinicalAnalysisResponse(BaseModel):
    id: str
    session_id: str
    generated_at: datetime
    systemic_analysis: str | None
    root_systems: list[RootSystemResponse]
    cascade_chains: list[CascadeChainResponse]
    key_patterns: list[KeyPatternResponse]
    actionable_insights: list[ActionableInsightResponse]
    analysis_source: str
    model_used: str | None
    disclaimer: str

@router.get("/{session_id}", response_model=ClinicalAnalysisResponse)
async def get_clinical_analysis(session_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    # Query ClinicalAnalysis by session_id
    # Return 404 if not found
```

### 4b. Register router in `api/app/main.py`

```python
from app.routers import clinical
app.include_router(clinical.router, prefix="/api/v1/clinical", tags=["clinical"])
```

---

## Wave 5: Frontend — API Client & Hook

### 5a. Add TypeScript interfaces in `web/src/lib/api-client.ts`

```typescript
export interface RootSystem {
  organ_system: string;
  confidence: string;
  reasoning: string;
  downstream_effects: string[];
}

export interface CascadeChain {
  chain: string[];
  mechanism: string;
  supporting_pathways: string[];
  key_conditions: string[];
}

export interface KeyPattern {
  pattern_name: string;
  conditions_involved: string[];
  shared_pathways: string[];
  clinical_significance: string;
  severity: string;
}

export interface ActionableInsight {
  priority: number;
  focus_area: string;
  reasoning: string;
  supported_by: string;
}

export interface ClinicalAnalysisData {
  id: string;
  session_id: string;
  generated_at: string;
  systemic_analysis: string | null;
  root_systems: RootSystem[];
  cascade_chains: CascadeChain[];
  key_patterns: KeyPattern[];
  actionable_insights: ActionableInsight[];
  analysis_source: string;
  model_used: string | null;
  disclaimer: string;
}
```

### 5b. Add API client method

```typescript
async getClinicalAnalysis(sessionId: string): Promise<ClinicalAnalysisData> {
  return this.fetch(`/api/v1/clinical/${sessionId}`);
}
```

### 5c. Add TanStack Query hook in `web/src/lib/hooks/use-api.ts`

```typescript
export function useClinicalAnalysis(sessionId: string | null) {
  const ready = useApiToken();
  return useQuery({
    queryKey: ["clinical-analysis", sessionId],
    queryFn: () => apiClient.getClinicalAnalysis(sessionId!),
    enabled: ready && !!sessionId,
    retry: false,
  });
}
```

### 5d. Invalidate on re-analyze

In `useAnalyzeReport()` `onSuccess`, add:
```typescript
queryClient.invalidateQueries({ queryKey: ["clinical-analysis", sessionId] });
```

---

## Wave 6: Frontend — Clinical Analysis Page

### 6a. New page: `web/src/app/dashboard/clinical-analysis/[id]/page.tsx`

**Layout (6 sections):**

1. **Header** — "Clinical Analysis" title + back link to report + "Powered by AI" badge showing `analysis_source`

2. **Medical Disclaimer Alert** — Amber alert box (same pattern as recovery page)

3. **Systemic Analysis Card** — Full narrative text (`systemic_analysis`). Rendered as prose with proper paragraph breaks. This is the main "story" of what's happening.

4. **Root Systems & Cascade Chains** — Visual layout:
   - Left column: Root systems as cards with confidence badges (high=red, medium=amber, low=green), reasoning text, and downstream effects as arrow-connected badges
   - Right column: Cascade chains rendered as flow diagrams: `Digestive → Hepatic → Hematologic → Neurological` with connecting arrows, mechanism text below, supporting pathway badges

5. **Key Patterns** — Grid of pattern cards, each showing:
   - Pattern name + severity badge (color-coded: critical/high/moderate/low)
   - Conditions involved as badges
   - Shared pathways listed
   - Clinical significance text

6. **Actionable Insights** — Numbered priority list:
   - Each item: priority number, focus area (bold), reasoning, "Supported by: ..." in muted text
   - Visual priority indicators (🔴 1, 🟠 2, 🟡 3)

7. **Footer Disclaimer** — Standard medical disclaimer

### 6b. Add navigation item in `web/src/app/dashboard/layout.tsx`

Add to dynamic nav items (between Insights and Recovery Plan):
```typescript
{ href: "/dashboard/clinical-analysis", label: "Clinical Analysis", icon: Microscope }
```

### 6c. Add link from report page

In `web/src/app/dashboard/report/[id]/page.tsx`, add a "Clinical Analysis" button alongside Insights and Recovery Plan buttons.

---

## Wave 7: Configuration & Environment

### 7a. Update `api/app/config.py`

Ensure these settings exist:
```python
ANTHROPIC_API_KEY: str = ""  # empty = template fallback
ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
```

### 7b. Update `.env`

```
ANTHROPIC_API_KEY=<user's API key>
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### 7c. Update `api/requirements.txt`

Add: `anthropic>=0.40.0`

### 7d. Docker considerations

The Anthropic Python SDK is a pure HTTP client — no subprocess or CLI needed. Works in Docker with just the `ANTHROPIC_API_KEY` env var passed to the Celery worker container.

---

## Files Modified (Summary)

| File | Action | Description |
|------|--------|-------------|
| `api/app/models/clinical_analysis.py` | **New** | ClinicalAnalysis SQLAlchemy model |
| `api/app/models/session.py` | **Modify** | Add `clinical_analysis` relationship |
| `api/app/services/clinical_analyzer.py` | **Modify** | Switch to Anthropic SDK, add metadata return |
| `api/app/tasks/analyze.py` | **Modify** | Add Step 6b (clinical analysis), promote systemic var |
| `api/app/routers/clinical.py` | **New** | GET /api/v1/clinical/{session_id} endpoint |
| `api/app/routers/reports.py` | **Modify** | Delete clinical analysis on report deletion |
| `api/app/main.py` | **Modify** | Register clinical router |
| `api/app/config.py` | **Modify** | Ensure ANTHROPIC_API_KEY + MODEL settings |
| `api/requirements.txt` | **Modify** | Add `anthropic` |
| `web/src/lib/api-client.ts` | **Modify** | Add interfaces + getClinicalAnalysis method |
| `web/src/lib/hooks/use-api.ts` | **Modify** | Add useClinicalAnalysis hook + cache invalidation |
| `web/src/app/dashboard/clinical-analysis/[id]/page.tsx` | **New** | Clinical analysis display page |
| `web/src/app/dashboard/layout.tsx` | **Modify** | Add nav item |
| `web/src/app/dashboard/report/[id]/page.tsx` | **Modify** | Add Clinical Analysis button |
| Alembic migration | **New** | Create clinical_analyses table |

## Dependency Order

```
Wave 1 (DB model + migration) → Wave 2 (LLM service refactor) → Wave 3 (pipeline integration)
                                                                → Wave 4 (API endpoint)
                                                                → Wave 5 (frontend client/hooks)
                                                                → Wave 6 (frontend page)
Wave 7 (config/env) — can be done anytime
```

## Verification

1. **Unit test**: Mock Anthropic SDK call, verify JSON parsing and template fallback
2. **Pipeline test**: Upload PDF → Analyze → verify `clinical_analyses` table has a record
3. **API test**: `GET /api/v1/clinical/{session_id}` returns structured response
4. **Frontend test**: Navigate to Clinical Analysis page, verify all 6 sections render
5. **Fallback test**: Remove `ANTHROPIC_API_KEY` → verify template analysis still works
6. **Re-analyze test**: Re-analyze → verify old clinical analysis is replaced
7. **Delete test**: Delete report → verify clinical analysis is also deleted
