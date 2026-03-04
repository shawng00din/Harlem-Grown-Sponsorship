# Harlem Grown Prospect Intelligence — Implementation Plan

## Pre-Work

1. Copy `sponsor_criteria_framework.md` into `knowledge_base/` (it will be loaded as the `"criteria"` collection)
2. Update CLAUDE.md httpx section to include full error-handling pattern:

```python
# All httpx calls must use:
async with httpx.AsyncClient(
    follow_redirects=True,   # Corporate URLs often redirect
    verify=False,             # Ignore SSL cert errors on corporate sites
    timeout=30.0,
) as client:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error fetching {url}: {e}")
        return None   # or partial data — never raise
```

---

## Phase 1 — Infrastructure

**Files to create (in order):**

### `docker-compose.yml`
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: hg_user
      POSTGRES_PASSWORD: hg_password
      POSTGRES_DB: harlem_grown
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
volumes:
  pgdata:
```

### `backend/sql/init.sql`
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### `.env`
Full env var template with all keys including new API vars:
- `COMPANIES_API_KEY`, `COMPANIES_API_BASE_URL`
- `DOUBLE_THE_DONATION_API_KEY`, `DOUBLE_THE_DONATION_BASE_URL`
- `PROPUBLICA_API_BASE_URL`
- `DISCOVERY_BATCH_SIZE`, `SEED_LIST_FALLBACK`

### `.gitignore`
Include: `.env`, `__pycache__/`, `*.pyc`, `backend/storage/`, `node_modules/`, `.next/`, `alembic/versions/*.py` (except keep 001_initial_schema.py)

### `backend/config.py`
Pydantic `Settings` class with all env vars including new API keys/URLs. Must export a singleton `settings` instance.

New fields vs. old:
```python
COMPANIES_API_KEY: str = ""
COMPANIES_API_BASE_URL: str = "https://api.thecompaniesapi.com/v2"
DOUBLE_THE_DONATION_API_KEY: str = ""
DOUBLE_THE_DONATION_BASE_URL: str = "https://doublethedonation.com/api/v2"
PROPUBLICA_API_BASE_URL: str = "https://projects.propublica.org/nonprofits/api/v2"
DISCOVERY_BATCH_SIZE: int = 50
SEED_LIST_FALLBACK: str = "./seed/curated_seed_list.json"
```

### `backend/database.py`
- `create_async_engine()` with `DATABASE_URL`
- `AsyncSessionLocal = async_sessionmaker(...)`
- `async def get_db()` — FastAPI dependency yielding `AsyncSession`
- Export `AsyncSessionLocal` for use in agent `log_step()` calls

### `backend/models/orm.py`
Six SQLAlchemy models:
- `Prospect` — company name, URL, status, alignment_score (Integer, 0-100), tier (String), archetype (String), confidence (String: HIGH/MEDIUM/LOW), source (String: "discovery"/"manual"), discovery_job_id (FK nullable)
- `Dossier` — esg_priorities JSONB, giving_patterns JSONB, csuite_contacts JSONB, matched_programs JSONB, matched_stories JSONB, archetype (String), outreach_brief (Text)
- `GeneratedLetter` — letter_body, briefing_doc, follow_up_path JSONB, is_current, version
- `ResearchJob` — status, step_log JSONB, current_step, prospect_id FK
- `KnowledgeChunk` — chunk_text, doc_source, collection, metadata JSONB, embedding Vector(1536)
- `DiscoveryJob` — status, filters JSONB, total_candidates (Integer), qualified_count (Integer), step_log JSONB, current_step

All UUID PKs via `uuid.uuid4`, all TIMESTAMPTZ timestamps.

**Removed:** `ChatMessage` model

### `backend/models/schemas.py`
Pydantic v2 schemas:
- `ProspectCreate`, `ProspectResponse` (with tier, archetype, confidence, nested dossier + letter)
- `QualificationResult` — 10 dimension scores dict, total_score (0-100), tier, archetype, confidence, go_no_go, key_signals, strongest_angle, biggest_gap, recommended_program_match, decision_maker_hypothesis, existing_partner_flag
- `ResearchResult` — outreach_brief, letter_body, briefing_doc, esg_priorities, giving_patterns, csuite_contacts, matched_programs, matched_stories, follow_up_path
- `DiscoveryJobCreate` (filters), `DiscoveryJobResponse`, `DiscoveryCandidateResponse`
- `ResearchJobResponse` (with step_log list)
- `LetterResponse`, `RegenerateRequest`
- `KnowledgeStatusResponse`

**Removed:** `ChatRequest`, `ChatMessageResponse`

### Alembic Setup
```bash
cd backend
alembic init alembic
# Edit alembic/env.py to use async engine + import Base from models.orm
# Edit alembic.ini sqlalchemy.url to use DATABASE_URL_SYNC
alembic revision --autogenerate -m "initial_schema"
```

The `alembic/env.py` must use `run_async_migrations()` pattern and import `Base` from `backend.models.orm`.

### `backend/requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
agno==1.3.0
anthropic==0.34.0
openai==1.40.0
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.3
pgvector==0.3.2
crawl4ai==0.3.74
pymupdf==1.24.10
pydantic==2.8.0
pydantic-settings==2.4.0
python-dotenv==1.0.1
httpx==0.27.0
tiktoken==0.7.0
numpy==1.26.4
python-multipart==0.0.12
sse-starlette==2.1.3
```

**Verification checkpoint:**
```bash
docker compose up -d
docker compose ps  # wait until healthy
psql postgresql://hg_user:hg_password@localhost:5432/harlem_grown -c "\dt"
# Must show: prospects, dossiers, generated_letters, research_jobs, knowledge_chunks, discovery_jobs
# Must NOT show: chat_messages
psql ... -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
# Must return 1 row
```

---

## Phase 2 — Tools

### `backend/tools/scraper.py`

Two functions, both wrapped in `try/except`:

```python
async def scrape_page(url: str) -> str:
    """
    Scrape a single URL and return clean markdown text.
    Use this to read a company's homepage, about page, or CSR page.
    """

async def scrape_site(base_url: str, max_pages: int = 5) -> str:
    """
    Crawl up to max_pages pages of a site and return concatenated markdown.
    Use this for sites where content is spread across multiple pages.
    """
```

Use `AsyncWebCrawler` from `crawl4ai`. Set `headless=True`. Return `result.markdown` or `result.extracted_content`. On failure, log a warning and return empty string — never raise.

### `backend/tools/pdf_extractor.py`

```python
async def extract_pdf_from_url(url: str) -> str:
    """
    Download a PDF from url and extract all text using PyMuPDF.
    Use this to read ESG reports, annual reports, or CSR PDFs.
    Returns extracted text, or empty string on failure.
    """
```

- Download with `httpx.AsyncClient(follow_redirects=True, verify=False, timeout=30.0)`
- Save to `settings.STORAGE_DIR/pdfs/` with sanitized filename
- Extract with `fitz.open()`
- Wrap entire function in `try/except` — return `""` on any failure

### `backend/tools/companies_api.py` (NEW)

```python
async def search_companies(
    city: str = "New York",
    industries: list[str] | None = None,
    min_employees: int = 200,
    limit: int = 50,
) -> list[dict]:
    """
    Search The Companies API for companies matching filters.
    Returns list of dicts: {name, domain, industry, employee_count, city, state, revenue_range}
    Falls back to curated_seed_list.json if API fails or credits exhausted.
    """

async def get_company_details(domain: str) -> dict | None:
    """
    Get detailed firmographic data for a single company by domain.
    Returns dict with HQ location, employee count, industry, revenue range.
    Falls back to None if API fails.
    """
```

- Uses `settings.COMPANIES_API_KEY` and `settings.COMPANIES_API_BASE_URL`
- Fallback: load from `settings.SEED_LIST_FALLBACK` JSON file

### `backend/tools/donation_api.py` (NEW)

```python
async def get_company_giving_programs(company_name: str) -> dict | None:
    """
    Query Double the Donation API for a company's volunteer and giving programs.
    Returns dict: {has_matching_gifts, has_volunteer_grants, has_vto, program_details}
    Falls back to None if API unavailable.
    """
```

- Uses `settings.DOUBLE_THE_DONATION_API_KEY` and `settings.DOUBLE_THE_DONATION_BASE_URL`
- Fallback: return None (qualifier falls back to web search)

### `backend/tools/propublica_api.py` (NEW)

```python
async def search_nonprofit_990(organization_name: str) -> list[dict]:
    """
    Search ProPublica Nonprofit Explorer for 990 filings.
    Use this to find giving history and grant amounts for foundations.
    Returns list of filing summaries.
    """

async def get_990_details(ein: str) -> dict | None:
    """
    Get detailed 990 filing data by EIN from ProPublica.
    Returns revenue, expenses, grants made, and grant recipients if available.
    """
```

- Uses `settings.PROPUBLICA_API_BASE_URL` (no API key needed — public API)
- Fallback: return empty list / None

### `backend/tools/directory_scraper.py` (NEW)

```python
async def search_bcorp_directory(location: str = "New York") -> list[dict]:
    """
    Scrape B Corp directory for certified companies in a location.
    Returns list of dicts: {name, domain, industry, certification_date}
    """

async def search_onepercentplanet(location: str = "New York") -> list[dict]:
    """
    Scrape 1% for the Planet member directory for companies in a location.
    Returns list of dicts: {name, domain, industry}
    """
```

- Uses Crawl4AI to scrape directory pages
- Wrapped in try/except — return empty list on failure

### `backend/tools/db_tools.py` (MODIFIED)

Agent-callable functions that query the DB and KB:

```python
async def search_programs_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Search the Harlem Grown programs knowledge base for programs relevant to the query.
    Returns list of dicts with chunk_text, similarity score.
    """

async def search_stories_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Search the Harlem Grown impact stories knowledge base for stories matching the query.
    Returns list of dicts with chunk_text, tags, similarity score.
    """

async def search_criteria_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Search the sponsor criteria framework for scoring guidance relevant to the query.
    Use this to find archetype profiles, scoring rubrics, and search criteria.
    """

async def get_prospect_data(prospect_id: str) -> dict:
    """
    Retrieve full prospect data including dossier from the database.
    """
```

**Removed:** Chat-related DB functions

### `seed/curated_seed_list.json` (NEW)

~100 NYC companies as API fallback. Structure:
```json
[
  {"name": "Goldman Sachs", "domain": "goldmansachs.com", "industry": "Financial Services", "employee_count": 40000, "city": "New York", "state": "NY"},
  ...
]
```

**Verification checkpoint:**
```python
import asyncio
from backend.tools.scraper import scrape_page
result = asyncio.run(scrape_page("https://example.com"))
assert len(result) > 100
print("Scraper OK:", result[:200])
```

---

## Phase 3 — RAG

### `knowledge_base/` — Five Markdown Files

Create all five files:
- `harlem_grown_overview.md` — mission, stats, founder story, key pitching stats
- `programs.md` — 7 programs with details
- `impact_stories.md` — 8-10 tagged stories
- `sponsorship_tiers.md` — Platinum/Gold/Silver/Community/Site Visit tiers
- `sponsor_criteria_framework.md` — copied from project root (10 dimensions, archetypes A-F, search criteria)

### `backend/rag/loader.py`

```python
COLLECTION_MAP = {
    "harlem_grown_overview": "overview",
    "programs": "programs",
    "impact_stories": "stories",
    "sponsorship_tiers": "tiers",
    "sponsor_criteria_framework": "criteria",
}

async def load_knowledge_base(force_reload: bool = False) -> int:
    """
    Load all markdown files from KNOWLEDGE_BASE_DIR into knowledge_chunks table.
    Returns count of chunks inserted.
    Skips if table is non-empty unless force_reload=True.
    """
```

Algorithm:
1. Check chunk count; return early if > 0 and not force_reload
2. If force_reload: `DELETE FROM knowledge_chunks`
3. For each `.md` file in `KNOWLEDGE_BASE_DIR`:
   - Determine collection name from `COLLECTION_MAP` using filename stem
   - Read content
   - Chunk using tiktoken `cl100k_base` encoder: 500 tokens, 50 token overlap
   - For each chunk: call OpenAI `text-embedding-3-small`, insert `KnowledgeChunk` row
4. Return total chunks inserted

### `backend/rag/retriever.py`

```python
async def similarity_search(
    query: str,
    collection: str,
    top_k: int = 5,
    session: AsyncSession = None,
) -> list[dict]:
    """
    Embed query with OpenAI and find top_k most similar chunks in the given collection.
    Returns list of dicts: {chunk_text, doc_source, metadata, similarity}
    """
```

Use the **exact** raw SQL pattern from CLAUDE.md — never ORM for this:
```python
result = await session.execute(
    text("""
        SELECT chunk_text, doc_source, metadata,
               1 - (embedding <=> :embedding::vector) AS similarity
        FROM knowledge_chunks
        WHERE collection = :collection
        ORDER BY embedding <=> :embedding::vector
        LIMIT :top_k
    """),
    {"embedding": str(query_embedding), "collection": collection, "top_k": top_k}
)
```

**Verification checkpoint:**
```python
from backend.rag.loader import load_knowledge_base
from backend.rag.retriever import similarity_search
count = asyncio.run(load_knowledge_base())
print(f"Loaded {count} chunks")
results = asyncio.run(similarity_search("youth farming programs", "programs", 3))
assert len(results) == 3
print(results[0]["chunk_text"][:200])
# Also verify criteria collection:
criteria = asyncio.run(similarity_search("volunteer engagement appetite", "criteria", 3))
assert len(criteria) == 3
```

---

## Phase 4 — Agents

### Pydantic Response Models

| Agent | Model |
|---|---|
| discovery.py | `DiscoveryResult` — list of candidate dicts with name, domain, industry, size, city |
| qualifier.py | `QualificationResult` — 10 dimension scores, total (0-100), tier, archetype, confidence, signals, angles |
| researcher.py | `ResearchResult` — outreach_brief, letter_body, briefing_doc, esg_priorities, giving_patterns, csuite_contacts, matched_programs, matched_stories, follow_up_path |

### `log_step()` Helper

Define in `backend/agents/team.py` (or a shared `backend/agents/utils.py`):

```python
async def log_step(job_id: str, step: str, status: str, message: str):
    async with AsyncSessionLocal() as session:
        job = await session.get(ResearchJob, job_id)
        log = job.step_log or []
        log.append({
            "step": step, "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        job.step_log = log
        job.current_step = step
        await session.commit()
```

Every agent's `run()` call must be bracketed by `log_step(..., "running", ...)` and `log_step(..., "complete", ...)`.

### `backend/agents/discovery.py` (NEW)

- Model: `Claude(id="claude-haiku-4-5-20251001")`
- Tools: `[search_companies, search_bcorp_directory, search_onepercentplanet]`
- Instructions: `DISCOVERY_INSTRUCTIONS` constant — describes filters (NYC metro, target sectors, 200+ employees), exclusion list (known HG partners), and output format
- `structured_outputs=True`, `response_model=DiscoveryResult`
- Output: raw candidate list of 200-500 companies with name, domain, industry, size, city
- No scoring — just structured API queries and deduplication

### `backend/agents/qualifier.py` (REWRITTEN)

- Model: `Claude(id="claude-haiku-4-5-20251001")`
- Tools: `[scrape_page, scrape_site, search_criteria_kb, get_company_giving_programs, get_company_details]`
- Instructions: `QUALIFIER_INSTRUCTIONS` constant — **must include the full 10-dimension rubric from `sponsor_criteria_framework.md` Parts 4-6**. Encodes:
  1. The 10 scoring dimensions with exact rubrics
  2. The archetype list (A-F) so the agent can pattern-match
  3. The disqualifying signals for fast-fail
  4. The threshold table (PRIORITY/STRONG/POSSIBLE/MONITOR/PASS)
- `structured_outputs=True`, `response_model=QualificationResult`
- `go_no_go = total_score >= 60`

**QualificationResult fields:**
```python
class QualificationResult(BaseModel):
    company_name: str
    website_url: str
    scores: dict  # 10 dimension scores, each 0-10
    total_score: int  # 0-100
    tier: str  # PRIORITY | STRONG | POSSIBLE | MONITOR | PASS
    archetype: str  # A-F or "None"
    confidence: str  # HIGH | MEDIUM | LOW
    go_no_go: bool  # True if total >= 60
    key_signals: list[str]  # 3-5 verbatim evidence quotes
    strongest_angle: str
    biggest_gap: str
    recommended_program_match: str
    decision_maker_hypothesis: str
    existing_partner_flag: bool
```

**Fast-fail logic:**
1. Is this company already in HG's known partner list? → Flag + stop
2. No NYC presence? → Score dimension 4 at 0, note likely below threshold
3. No CSR/giving page? → Score capacity and accessibility low, confidence=LOW

### `backend/agents/researcher.py` (REWRITTEN)

- Model: `Claude(id="claude-sonnet-4-5-20250514")`
- Tools: `[scrape_page, scrape_site, extract_pdf_from_url, search_programs_kb, search_stories_kb, search_criteria_kb, search_nonprofit_990]`
- Instructions: `RESEARCHER_INSTRUCTIONS` constant — **uses archetype from qualifier output to set letter tone and lead angle**. Tasks:
  1. Find named CSR/foundation contacts (title: CSR Director, VP Community Affairs, Head of Philanthropy)
  2. Pull recent grants or partnerships from news/press releases
  3. Identify any Harlem or upper Manhattan connection
  4. RAG-match HG programs and stories to company values (uses `search_programs_kb`, `search_stories_kb`)
  5. Draft tailored pitch hook based on archetype
  6. Write personalized outreach letter using archetype-specific lead angle
  7. Produce one-page outreach brief for human review
- `structured_outputs=True`, `response_model=ResearchResult`
- Output includes: `letter_body`, `briefing_doc`, `outreach_brief`, `esg_priorities`, `giving_patterns`, `csuite_contacts`, `matched_programs`, `matched_stories`, `follow_up_path`

### `backend/agents/team.py` (REWRITTEN)

```python
def create_research_team() -> Team:
    return Team(
        name="Harlem Grown Prospect Research Team",
        mode="sequential",
        model=Claude(id="claude-sonnet-4-5-20250514"),
        agents=[
            create_qualifier_agent(),
            create_researcher_agent(),
        ],
        show_progress=True,
        enable_team_context=True,
    )
```

**Tier gate:** After qualifier runs, check `tier`. If POSSIBLE, MONITOR, or PASS: save qualifier results, skip researcher, mark job as complete with qualifier-only results. Only run researcher on PRIORITY or STRONG.

### Deleted Files
- `backend/agents/narrative_matcher.py` — RAG matching now handled by researcher
- `backend/agents/writer.py` — letter writing now handled by researcher
- `backend/agents/chat_agent.py` — chat co-pilot removed

**Verification checkpoint:**
```python
from backend.agents.qualifier import create_qualifier_agent
agent = create_qualifier_agent()
result = agent.run("Qualify https://www.goldmansachs.com as a Harlem Grown prospect")
print(f"Score: {result.total_score}/100, Tier: {result.tier}, Archetype: {result.archetype}")
# Should be ~72, STRONG, C
assert result.go_no_go == True
assert result.tier in ["PRIORITY", "STRONG"]
```

---

## Phase 5 — API

### `backend/routers/prospects.py`
- `POST /api/prospects/` — create, validate URL, set status="queued"
- `GET /api/prospects/` — list ordered by alignment_score DESC, include dossier + current letter + tier + archetype in response
- `GET /api/prospects/{id}` — full detail with dossier + letters + 10-dim breakdown
- `DELETE /api/prospects/{id}` — cascade deletes dossier, letters, jobs

### `backend/routers/research.py` (MODIFIED)

**Trigger endpoint** `POST /api/research/{prospect_id}/run`:
1. Create `ResearchJob` row (status="pending")
2. Launch `BackgroundTasks.add_task(run_research_pipeline, prospect_id, job_id)`
3. Return `{"job_id": job_id}`

**Pipeline function** `run_research_pipeline(prospect_id, job_id)`:
1. `log_step(job_id, "qualifier", "running", "Scoring 10 dimensions...")`
2. Run qualifier agent
3. Save qualification result to prospect (score 0-100, tier, archetype, confidence, breakdown)
4. `log_step(job_id, "qualifier", "complete", f"Score: {score}/100 — {tier} ({archetype})")`
5. If tier not in [PRIORITY, STRONG]: mark job complete, prospect status="qualified", return
6. `log_step(job_id, "researcher", "running", "Deep-diving ESG priorities...")`
7. Run researcher agent (receives qualifier output in team context)
8. Save dossier (with archetype, outreach_brief) and generated letter to DB
9. `log_step(job_id, "researcher", "complete", "Outreach brief + letter ready")`
10. Mark prospect status="complete", job status="complete"
11. On any exception: `log_step(job_id, step, "error", str(e))`, mark job failed

**SSE Stream endpoint** `GET /api/research/stream/{job_id}`:
- Uses `sse_starlette.sse.EventSourceResponse`
- Generator polls `research_jobs.step_log` every 500ms
- Emits each new step event as SSE
- Terminates when job status is "complete" or "failed"
- 2 steps: qualifier → researcher (not 4)

### `backend/routers/letters.py`
- `GET /api/letters/{prospect_id}` — return current letter (is_current=True)
- `POST /api/letters/{prospect_id}/regenerate` — accepts `{"instructions": "..."}`, runs researcher agent with new instructions + archetype context, sets old letter is_current=False, saves new one

### `backend/routers/discovery.py` (NEW)

**Trigger endpoint** `POST /api/discovery/run`:
1. Accept filters: `{industries, min_employees, location, ...}`
2. Create `DiscoveryJob` row (status="pending", filters=request.filters)
3. Launch background task `run_discovery_pipeline(job_id)`
4. Return `{"job_id": job_id}`

**Pipeline function** `run_discovery_pipeline(job_id)`:
1. `log_step(job_id, "discovery", "running", "Searching company databases...")`
2. Run discovery agent — get raw candidate list
3. Update discovery_jobs.total_candidates
4. `log_step(job_id, "discovery", "complete", f"Found {n} candidates")`
5. `log_step(job_id, "qualifier", "running", "Qualifying candidates...")`
6. For each candidate batch: run qualifier, create prospect rows, update qualified_count
7. `log_step(job_id, "qualifier", "complete", f"Qualified {q} of {n} candidates")`
8. Mark job complete

**Results endpoint** `GET /api/discovery/results/{job_id}`:
- Return all prospects linked to this discovery job, ordered by score DESC

**Batch research endpoint** `POST /api/discovery/research-batch`:
- Accept `{"job_id": "...", "tiers": ["PRIORITY", "STRONG"]}`
- For each qualifying prospect: create research job, launch researcher
- Return list of research job IDs

**SSE Stream endpoint** `GET /api/discovery/stream/{job_id}`:
- Same pattern as research stream but polls `discovery_jobs.step_log`
- 3 steps: discovery → qualifier → researcher

### `backend/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_knowledge_base()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_URL], ...)
app.include_router(prospects_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(letters_router, prefix="/api")
app.include_router(discovery_router, prefix="/api")

@app.post("/api/knowledge/reload", ...)  # Force KB reload
@app.get("/api/knowledge/status", ...)  # KB chunk count + doc list
@app.get("/health")  # Returns {"status": "ok", "service": "harlem-grown-prospect-intelligence"}
```

**Removed:** chat router

**Verification checkpoint:**
```bash
uvicorn backend.main:app --reload --port 8000
curl http://localhost:8000/health
# → {"status": "ok", "service": "harlem-grown-prospect-intelligence"}
curl http://localhost:8000/docs
# Swagger UI must show all routes including /api/discovery/* — must NOT show /api/chat/*
```

---

## Phase 6 — Frontend

### Bootstrap
```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card badge table tabs textarea dialog progress
npm install @tanstack/react-query axios eventsource-parser lucide-react recharts
```

### `frontend/lib/types.ts`
TypeScript interfaces matching every Pydantic schema:
- `Prospect` (with tier, archetype, confidence, alignment_score 0-100)
- `Dossier` (with archetype, outreach_brief, 10-dim scores)
- `GeneratedLetter`, `ResearchJob`, `DiscoveryJob`
- `QualificationScores` (10 named dimension scores)
- `StepEvent`, `SSEEvent` (union: step | complete | error | timeout)
- `DiscoveryCandidate`
- No `any` types anywhere

**Removed:** `ChatMessage`

### `frontend/lib/api.ts`
Typed axios client with base URL from env. Functions for:
- `createProspect()`, `listProspects()`, `getProspect()`, `deleteProspect()`
- `runResearch()`, `getLetter()`, `regenerateLetter()`
- `runDiscovery()`, `getDiscoveryResults()`, `runBatchResearch()`
- `getKnowledgeStatus()`, `reloadKnowledge()`

**Removed:** `sendChatMessage()`, `getChatHistory()`

### `frontend/app/layout.tsx`
Root layout with ReactQuery provider, Navbar, and globals.

### `frontend/components/Navbar.tsx`
Links to: Dashboard (`/`), Discovery (`/discovery`), Research (`/research`).

**Removed:** Chat link

### `frontend/components/AlignmentScoreBar.tsx`
Visual bar for 0-100 score. Show 10 subcategory breakdown with mini bars. Tier badge (PRIORITY=green, STRONG=blue, POSSIBLE=yellow, MONITOR=gray, PASS=red). Archetype label (e.g., "Archetype C: The Resilient Financier").

### `frontend/components/ProspectTable.tsx`
Sortable table of all prospects. Columns: Company logo (Clearbit), Name, Score (0-100), Tier badge, Archetype label, Confidence indicator, Status badge, Actions (View, Delete). Click row → navigate to `/prospects/[id]`.

### `frontend/app/page.tsx` — Dashboard
- Summary stats: total prospects, by tier (PRIORITY/STRONG/POSSIBLE/MONITOR/PASS), in-progress, completed
- `ProspectTable` component
- React Query for data fetching

### `frontend/components/AgentProgressStream.tsx` — SINGLE-COMPANY RESEARCH
- `"use client"` directive
- Props: `jobId: string`, `onComplete: () => void`
- Use native `EventSource` connecting to `/api/research/stream/{jobId}`
- Render vertical stepper: **2 steps** (Qualifier, Researcher)
- Each step shows: spinner (running) | green checkmark (complete) | red X (error) | gray dot (pending)
- Show live message text under the active step
- On `type: "complete"`: call `onComplete()`, close EventSource
- On `type: "error"`: show red error state, close EventSource

### `frontend/components/BatchProgressStream.tsx` — BATCH DISCOVERY (NEW)
- `"use client"` directive
- Props: `jobId: string`, `onComplete: () => void`
- Use native `EventSource` connecting to `/api/discovery/stream/{jobId}`
- Render vertical stepper: **3 steps** (Discovery, Qualifier, Researcher)
- Show progress counts in messages ("Qualifying 47/200 candidates...")
- Same visual pattern as AgentProgressStream

### `frontend/components/DiscoveryResults.tsx` (NEW)
- `"use client"` directive
- Props: `jobId: string`
- Fetch results from `/api/discovery/results/{jobId}`
- Sortable/filterable table: Company, Score (0-100), Tier badge, Archetype, Top Signal, Confidence
- Filter buttons by tier
- "Research All PRIORITY+STRONG" button → calls `runBatchResearch()`

### `frontend/app/discovery/page.tsx` (NEW)
- `"use client"`
- Filter form: Industries (multi-select), Min Employees, Location
- On submit: call `runDiscovery(filters)` → render `BatchProgressStream`
- On complete: render `DiscoveryResults`

### `frontend/app/research/page.tsx`
- `"use client"`
- Form: Company Name + Website URL + Submit
- On submit: call `createProspect()` → `runResearch()` → render `AgentProgressStream`
- On complete: navigate to `/prospects/[id]`

### `frontend/components/DossierCard.tsx`
Display sections:
- Company logo (Clearbit) + name + URL
- Archetype badge (e.g., "C: The Resilient Financier")
- `AlignmentScoreBar` (10-dim breakdown, 0-100)
- Confidence indicator (HIGH=green, MEDIUM=yellow, LOW=red with "Limited CSR data" note)
- Outreach Brief (text block)
- ESG Priorities as badge list
- Giving patterns (range, preferred types, past partners)
- C-suite contacts list (name, title, is_primary indicator)
- Matched Programs (top 3 with relevance reason)
- Matched Stories (top 3 with tags)

### `frontend/components/LetterEditor.tsx`
- `"use client"`
- Display letter body in a serif-font card (font-serif class)
- "Rewrite with Instructions" button → opens textarea Dialog
- On submit: call `regenerateLetter(prospectId, instructions)` → update displayed letter
- Show loading state during regeneration

### `frontend/app/prospects/[id]/page.tsx`
- Tabbed layout: Dossier | Letter | Follow-up Path
- `DossierCard` in first tab
- `LetterEditor` in second tab
- Follow-up path rendered as numbered step list in third tab

### Deleted Files
- `frontend/components/ChatInterface.tsx`
- `frontend/app/chat/page.tsx`

**Verification checkpoint:**
- Open http://localhost:3000
- Dashboard loads, shows ProspectTable with tier badges and archetype labels
- Navigate to /discovery, run batch — BatchProgressStream shows 3 steps
- Navigate to /research, add Goldman Sachs — AgentProgressStream shows 2 steps
- Navigate to /prospects/[id], dossier shows 10-dim breakdown + archetype badge
- Click "Rewrite with Instructions" on LetterEditor — regeneration works

---

## Phase 7 — Seed Data

### `seed/curated_seed_list.json`
~100 NYC companies across target sectors as API fallback. Structured as array of objects with name, domain, industry, employee_count, city, state.

### `seed/seed_demo_data.py`

Pre-load 4 completed prospects with realistic dossiers + letters. Use `DATABASE_URL_SYNC` (sync SQLAlchemy) for simplicity.

**The four companies (rescaled to 0-100):**

| Company | Score | Tier | Archetype | Status |
|---|---|---|---|---|
| Whole Foods Market | 88 | PRIORITY | A ("The Mission Soulmate") | complete |
| Northwell Health | 79 | STRONG | B ("The Community Health Champion") | complete — mark as existing partner |
| Goldman Sachs | 72 | STRONG | C ("The Resilient Financier") | complete |
| Salesforce | 63 | STRONG | E ("The Tech Neighbor") | complete |

**10-dimension breakdowns per company:**

**Whole Foods (88, PRIORITY, A):**
Food/Nutrition=10, Youth/Education=6, Sustainability=9, NYC Proximity=8, Volunteer=8, Capacity=9, Values Match=10, Decision-Maker=7, Sector Fit=10, Longevity=8, Confidence=HIGH

**Northwell Health (79, STRONG, B):**
Food/Nutrition=7, Youth/Education=6, Sustainability=5, NYC Proximity=9, Volunteer=9, Capacity=8, Values Match=7, Decision-Maker=8, Sector Fit=10, Longevity=8, Confidence=HIGH

**Goldman Sachs (72, STRONG, C):**
Food/Nutrition=4, Youth/Education=7, Sustainability=5, NYC Proximity=9, Volunteer=7, Capacity=10, Values Match=6, Decision-Maker=7, Sector Fit=9, Longevity=8, Confidence=HIGH

**Salesforce (63, STRONG, E):**
Food/Nutrition=3, Youth/Education=7, Sustainability=7, NYC Proximity=7, Volunteer=8, Capacity=8, Values Match=5, Decision-Maker=5, Sector Fit=7, Longevity=6, Confidence=MEDIUM

Each seed entry includes:
- `Prospect` row with alignment_score, tier, archetype, confidence, status="complete"
- `Dossier` row with realistic JSONB for esg_priorities, giving_patterns, csuite_contacts, matched_programs, matched_stories, archetype, outreach_brief
- `GeneratedLetter` row with letter_body, briefing_doc, follow_up_path, is_current=True
- For Northwell: add a note in the letter/briefing that they're an existing partner — "EXISTING PARTNER — Do Not Contact"

**Verification checkpoint:**
```bash
python seed/seed_demo_data.py
# Should print: "Seeded 4 prospects successfully"
# Open http://localhost:3000 — dashboard shows 4 prospects sorted by score (0-100)
# Tier badges visible: 1 PRIORITY (Whole Foods), 3 STRONG
# Archetype labels visible
```

---

## Critical Cross-Cutting Rules (Never Violate)

1. **No `Base.metadata.create_all()`** — Alembic always
2. **No ChromaDB, no LangChain, no LangGraph, no Firecrawl** — use the stack as specified
3. **Scraping failures are non-fatal** — all Crawl4AI calls in `try/except`, return `""` on failure
4. **SSE stream never blocks** — research runs in FastAPI `BackgroundTasks`, SSE polls `step_log` every 500ms
5. **Embeddings are OpenAI only** — `text-embedding-3-small`, 1536 dims, never Anthropic
6. **pgvector similarity query is raw SQL** — use the exact `<=>` operator pattern, never ORM
7. **Config always from `settings`** — import `from backend.config import settings`, never `os.environ`
8. **Agent system prompts are module-level constants** — `QUALIFIER_INSTRUCTIONS = """..."""`
9. **All httpx clients**: `follow_redirects=True, verify=False, timeout=30.0` wrapped in `try/except httpx.HTTPError`
10. **Alembic async env** — `alembic/env.py` must use `run_async_migrations()` pattern
11. **No `any` in TypeScript** — all types from `lib/types.ts`
12. **Clearbit logo API** — `https://logo.clearbit.com/{domain}` for all company logos
13. **API fallbacks mandatory** — every external API call (Companies API, Double the Donation, ProPublica, B Corp, 1% Planet) must have a fallback path
14. **Researcher gated on tier** — only runs on PRIORITY and STRONG. Never on POSSIBLE, MONITOR, or PASS
15. **Archetype flows through pipeline** — qualifier assigns, researcher uses for letter tone, UI displays
16. **Confidence flag surfaced** — LOW confidence (thin CSR data) must be visible to user, not hidden
