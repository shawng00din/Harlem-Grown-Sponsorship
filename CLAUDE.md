# CLAUDE.md — Harlem Grown Prospect Intelligence System

This file is your primary orientation for this codebase. Read it fully before writing any code. When in doubt about a pattern or decision, check here first, then check the PRD (harlem_grown_prd.md).

## What This System Does

A multi-agent AI system that helps Harlem Grown (NYC urban farming nonprofit) identify and prioritize corporate sponsors. It supports two flows:

1. **Batch Discovery** — Discovers candidate companies via structured API queries (The Companies API, B Corp/1% for Planet directories), filtered by NYC presence, sector, and size
2. **Qualification** — Scores each candidate on 10 dimensions (0-100) with archetype assignment (A-F) and tier classification (PRIORITY/STRONG/POSSIBLE/MONITOR/PASS)
3. **Deep Research** — For PRIORITY and STRONG tier companies only: produces an outreach brief + draft personalized letter using RAG-matched HG programs/stories
4. **Single-Company Live Research** — Staff enters a company name + URL, system qualifies and (if tier qualifies) researches in real time with SSE progress
5. **Letter Regeneration** — Staff can rewrite letters with custom instructions ("make it lead with the volunteer day angle")

## Stack — Non-Negotiable

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async throughout |
| Agents | Agno | NOT LangChain, NOT LangGraph |
| LLM | Anthropic Claude | Sonnet 4.5 for reasoning, Haiku 4.5 for qualifier + discovery |
| Database | PostgreSQL 16 + pgvector | Single DB for relational + vector data |
| ORM | SQLAlchemy 2.0 async + Alembic | NO raw SQL except pgvector similarity query |
| Scraping | Crawl4AI | NOT Firecrawl, NOT BeautifulSoup |
| PDF | PyMuPDF (fitz) | |
| Embeddings | OpenAI text-embedding-3-small | 1536 dimensions |
| Frontend | Next.js 14 App Router + Tailwind + shadcn/ui | |
| Storage | Local filesystem ./backend/storage/ | No S3, no cloud storage |
| Firmographic Data | The Companies API | Free tier, 500 credits. NYC + sector + size filters |
| Volunteer/Giving Data | Double the Donation API | Volunteer programs, VTO, matching gifts |
| ESG Pre-qualification | B Corp directory, 1% for the Planet directory | Scraped via Crawl4AI |
| Nonprofit Filings | ProPublica Nonprofit Explorer API | 990 data for giving history |

Never suggest switching these. If you hit a limitation, solve it within the stack.

## Project Structure

```
harlem-grown-prospect/
├── .env                        # Never commit. See section below for all vars.
├── docker-compose.yml          # Postgres + pgvector ONLY
├── harlem_grown_prd.md         # Full PRD — reference for deep detail
├── CLAUDE.md                   # This file
│
├── backend/
│   ├── main.py                 # FastAPI app + lifespan (KB init on startup)
│   ├── config.py               # Pydantic Settings — all env vars loaded here
│   ├── database.py             # Async engine, AsyncSessionLocal, get_db dep
│   ├── alembic/                # Migrations — always use Alembic, never raw DDL
│   ├── sql/init.sql            # CREATE EXTENSION vector; (runs on DB init)
│   ├── models/
│   │   ├── orm.py              # All SQLAlchemy models
│   │   └── schemas.py          # All Pydantic request/response schemas
│   ├── agents/
│   │   ├── team.py             # Agno Team (sequential, 2 agents: Qualifier → Researcher)
│   │   ├── discovery.py        # Agno Agent — Haiku 4.5, batch candidate generation
│   │   ├── qualifier.py        # Agno Agent — Haiku 4.5, 10-dim scoring (0-100)
│   │   └── researcher.py       # Agno Agent — Sonnet 4.5, deep research + letter + brief
│   ├── tools/
│   │   ├── scraper.py          # Crawl4AI wrappers (scrape_page, scrape_site)
│   │   ├── pdf_extractor.py    # PyMuPDF — download + extract PDF text
│   │   ├── db_tools.py         # Agent-callable DB queries (passed to Agent(tools=[]))
│   │   ├── companies_api.py    # The Companies API — firmographic queries
│   │   ├── donation_api.py     # Double the Donation API — volunteer/giving programs
│   │   ├── propublica_api.py   # ProPublica Nonprofit Explorer — 990 data
│   │   └── directory_scraper.py # B Corp + 1% for the Planet directory scrapers
│   ├── rag/
│   │   ├── loader.py           # Chunk KB docs → embed → insert into knowledge_chunks
│   │   └── retriever.py        # similarity_search() using pgvector <=> operator
│   ├── routers/
│   │   ├── prospects.py        # CRUD
│   │   ├── research.py         # Trigger research + SSE stream
│   │   ├── letters.py          # Get letter + regenerate with instructions
│   │   └── discovery.py        # Batch discovery + SSE stream
│   └── storage/
│       ├── pdfs/               # Downloaded ESG report PDFs
│       └── exports/            # Exported letters/briefings
│
├── knowledge_base/             # Markdown docs — loaded into pgvector on startup
│   ├── harlem_grown_overview.md
│   ├── programs.md
│   ├── impact_stories.md
│   ├── sponsorship_tiers.md
│   └── sponsor_criteria_framework.md
│
├── frontend/
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx            # Dashboard
│   │   ├── prospects/[id]/page.tsx  # Dossier + letter view
│   │   ├── research/page.tsx   # Add prospect + run single-company research
│   │   └── discovery/page.tsx  # Batch discovery flow
│   ├── components/
│   │   ├── AgentProgressStream.tsx  # SSE visualizer — single-company (2 steps)
│   │   ├── BatchProgressStream.tsx  # SSE visualizer — batch discovery (3 steps)
│   │   ├── LetterEditor.tsx    # Letter display + regenerate with instructions
│   │   ├── DossierCard.tsx     # Company dossier display (10-dim breakdown)
│   │   ├── DiscoveryResults.tsx # Batch discovery results table
│   │   ├── ProspectTable.tsx   # Sortable prospect queue (tier + archetype columns)
│   │   └── AlignmentScoreBar.tsx # 0-100 score bar, 10 dims, tier badge, archetype label
│   └── lib/
│       ├── api.ts              # Typed axios API client
│       └── types.ts            # TypeScript interfaces
│
└── seed/
    ├── seed_demo_data.py       # Pre-loads 4 demo prospects for demo
    └── curated_seed_list.json  # ~100 NYC companies as API fallback
```

## Environment Variables

All loaded via `backend/config.py` using pydantic-settings. Never access `os.environ` directly anywhere in the codebase — always import from `config.py`.

```env
# Anthropic — all agent LLM calls
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI — embeddings ONLY (text-embedding-3-small)
OPENAI_API_KEY=sk-...

# Database — matches docker-compose.yml exactly
DATABASE_URL=postgresql+asyncpg://hg_user:hg_password@localhost:5432/harlem_grown
DATABASE_URL_SYNC=postgresql://hg_user:hg_password@localhost:5432/harlem_grown

# Storage
STORAGE_DIR=./backend/storage
KNOWLEDGE_BASE_DIR=./knowledge_base

# App
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
LOG_LEVEL=INFO

# Embedding
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
EMBEDDING_CHUNK_SIZE=500
EMBEDDING_CHUNK_OVERLAP=50

# The Companies API
COMPANIES_API_KEY=...
COMPANIES_API_BASE_URL=https://api.thecompaniesapi.com/v2

# Double the Donation API
DOUBLE_THE_DONATION_API_KEY=...
DOUBLE_THE_DONATION_BASE_URL=https://doublethedonation.com/api/v2

# ProPublica Nonprofit Explorer
PROPUBLICA_API_BASE_URL=https://projects.propublica.org/nonprofits/api/v2

# Discovery
DISCOVERY_BATCH_SIZE=50
SEED_LIST_FALLBACK=./seed/curated_seed_list.json
```

## Database Tables

Six tables. All UUIDs as primary keys. All use TIMESTAMPTZ for timestamps.

| Table | Purpose |
|---|---|
| prospects | Company name, URL, status, alignment_score (0-100), tier, archetype, confidence, source, discovery_job_id |
| dossiers | ESG priorities, giving patterns, contacts, matched content (all JSONB), archetype, outreach_brief |
| generated_letters | Letter body, briefing doc, version history, follow-up path |
| research_jobs | Job status + step_log JSONB array (feeds SSE stream) |
| knowledge_chunks | RAG — text chunks + vector(1536) embedding column |
| discovery_jobs | Batch discovery job: status, filters JSONB, total_candidates, qualified_count, step_log JSONB |

**Critical: pgvector similarity query pattern**

```python
# Always use this exact pattern for similarity search — never ORM for this query
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

## Migrations

Always use Alembic. Never modify the DB schema with raw SQL or `Base.metadata.create_all()`.

```bash
# Create new migration after changing orm.py
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Agent Architecture

### Flow 1: Batch Discovery Pipeline

```
Discovery → Qualifier (batch) → Researcher (PRIORITY + STRONG only)
```

1. **Discovery Agent** generates raw candidate list (200-500 companies) from The Companies API + directories
2. **Qualifier Agent** scores each candidate on 10 dimensions (0-100), assigns archetype + tier
3. **Researcher Agent** runs only on PRIORITY (80-100) and STRONG (60-79) companies — produces outreach brief + draft letter

### Flow 2: Single-Company Live Research

```
Qualifier → Researcher (if tier qualifies)
```

1. Staff enters company name + URL
2. **Qualifier** scores on 10 dimensions, assigns tier
3. If PRIORITY or STRONG: **Researcher** runs (deep research + letter + brief)
4. If POSSIBLE or below: qualifier results saved, no researcher run

Built as an `agno.team.Team` with `mode="sequential"`. Each agent:
- Receives prior agents' outputs in shared team context
- Returns a structured Pydantic model (`structured_outputs=True`)
- Logs progress to `research_jobs.step_log` via `log_step()` helper

### Agent → Model Mapping (Demo)

| Agent | Model ID | Reason |
|---|---|---|
| Discovery | `claude-haiku-4-5-20251001` | Structured API queries — fast and cheap |
| Qualifier | `claude-haiku-4-5-20251001` | Structured scoring rubric with clear rules — Haiku handles this well |
| Researcher | `claude-sonnet-4-5-20250514` | Complex multi-page synthesis + letter writing + RAG matching |

**Production cost-down targets** (test after demo, downgrade one at a time):
- Researcher → Sonnet 3.5 (extraction-heavy portions, keep Sonnet 4.5 for letter writing)

### Agent Tools Pattern

Tools are plain async Python functions with type hints and docstrings. The docstring is what the LLM reads to decide when to call the tool. Pass them as a list to `Agent(tools=[fn1, fn2])`.

```python
async def scrape_page(url: str) -> str:
    """
    Scrape a single URL and return clean markdown text.
    Use this to read a company's homepage, about page, or CSR page.
    """
    ...
```

### Step Logging Pattern

Every agent must call this at the start and end of its work so the SSE stream has events to emit to the frontend:

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

Valid step names: `"discovery"`, `"qualifier"`, `"researcher"`

## Data Pipelines

Four data pipelines feed the 10 scoring dimensions. Each must have a fallback.

### Pipeline A — Structured Firmographics
- **Source:** The Companies API (free tier, 500 credits)
- **Feeds dimensions:** 4 (NYC/Harlem Proximity), 6 (Giving Capacity via revenue/headcount proxy), 9 (Sector Narrative Fit via industry code)
- **Failure mode:** Fall back to `curated_seed_list.json` for discovery; for single-company, scrape homepage for HQ location

### Pipeline B — Unstructured CSR Content
- **Source:** Crawl4AI + Claude inference
- **Feeds dimensions:** 1 (Food & Nutrition), 2 (Youth & Education), 3 (Environmental Sustainability), 7 (ESG Values Language Match)
- **Failure mode:** If CSR page not found, score dimensions 1, 2, 3, 7 at 2-3 and flag confidence=LOW. This is a known single point of failure — 4 dimensions from one page

### Pipeline C — Volunteer/Giving Programs
- **Source:** Double the Donation API
- **Feeds dimensions:** 5 (Employee Volunteer Appetite), partial 10 (Partnership Longevity from program age/history)
- **Failure mode:** Fall back to web search for "{company} employee volunteer program VTO"

### Pipeline D — Decision-Maker Discovery
- **Source:** Web search (LinkedIn, company pages)
- **Feeds dimension:** 8 (Decision-Maker Accessibility)
- **Failure mode:** ~50% automated coverage. Flag as "manual research needed" when not found. This is the weakest pipeline — acceptable for demo

## RAG Pattern

The knowledge base lives in `knowledge_base/*.md`. On startup (`main.py` lifespan), the app checks if `knowledge_chunks` table is empty — if so, loads all docs.

Collection names (used to filter similarity search):
- `"programs"` — from programs.md
- `"stories"` — from impact_stories.md
- `"overview"` — from harlem_grown_overview.md
- `"tiers"` — from sponsorship_tiers.md
- `"criteria"` — from sponsor_criteria_framework.md

Chunk size: 500 tokens, 50 token overlap. Use `tiktoken` `cl100k_base` encoder.

Embedding: Always `text-embedding-3-small` via OpenAI SDK. 1536 dimensions. Never use Anthropic for embeddings.

Force reload: Expose `POST /api/knowledge/reload` so the team can refresh after editing the markdown files without restarting the server.

## API Routes

```
POST   /api/prospects/                    Create prospect
GET    /api/prospects/                    List all (ordered by score desc)
GET    /api/prospects/{id}                Get single prospect
DELETE /api/prospects/{id}                Delete prospect

POST   /api/research/{prospect_id}/run    Trigger single-company research (returns job_id)
GET    /api/research/stream/{job_id}      SSE stream of agent progress (2 steps: qualifier → researcher)

GET    /api/letters/{prospect_id}         Get current letter
POST   /api/letters/{prospect_id}/regenerate  Rewrite with instructions

POST   /api/discovery/run                 Trigger batch discovery job (returns job_id)
GET    /api/discovery/stream/{job_id}     SSE stream of batch progress (3 steps: discovery → qualifier → researcher)
GET    /api/discovery/results/{job_id}    Get discovery results (qualified candidates)
POST   /api/discovery/research-batch      Trigger researcher on all PRIORITY+STRONG from a discovery job

POST   /api/knowledge/reload              Re-ingest knowledge base docs
GET    /api/knowledge/status              KB chunk count + doc list

GET    /health                            Health check
```

## SSE Event Schema

The frontend progress stream components expect this exact shape:

```json
// Progress event
{ "type": "step", "step": "qualifier", "status": "running", "message": "Scoring 10 dimensions..." }
{ "type": "step", "step": "qualifier", "status": "complete", "message": "Score: 78/100 — STRONG (Archetype C)" }
{ "type": "step", "step": "researcher", "status": "running", "message": "Deep-diving ESG priorities..." }
{ "type": "step", "step": "researcher", "status": "complete", "message": "Outreach brief + letter ready" }

// Terminal events
{ "type": "complete", "job_id": "..." }
{ "type": "error", "message": "...", "step": "qualifier" }
{ "type": "timeout" }
```

**Single-company flow:** 2 steps (qualifier, researcher)
**Batch discovery flow:** 3 steps (discovery, qualifier, researcher)

## Frontend Conventions

- **Framework**: Next.js 14 App Router. All data fetching in page components via React Query.
- **Styling**: Tailwind only. No inline styles. No CSS modules.
- **Components**: shadcn/ui for primitives (Button, Card, Badge, Table, Tabs, Textarea, Dialog).
- **API calls**: Always through `lib/api.ts`. Never fetch directly in components.
- **Streaming**: Use native `EventSource` for SSE. Use custom hook `useSSE` where possible.
- **Types**: All API response types defined in `lib/types.ts`. No `any`.
- **Logo fetching**: Use Clearbit Logo API — free, no key needed: `https://logo.clearbit.com/{domain}` e.g. `https://logo.clearbit.com/goldmansachs.com`

### Key Frontend Components

**AgentProgressStream** — Shows a vertical stepper for single-company research: 2 steps (Qualifier, Researcher). Spinner on current step, checkmarks on complete, live log message. Connects to `/api/research/stream/{job_id}` via EventSource.

**BatchProgressStream** — Shows a vertical stepper for batch discovery: 3 steps (Discovery, Qualifier, Researcher). Includes progress counts ("Qualifying 47/200 candidates..."). Connects to `/api/discovery/stream/{job_id}` via EventSource.

**LetterEditor** — Displays the generated letter in a serif font card. Has a "Rewrite with Instructions" button that opens an input. User types something like "make it more casual" or "lead with volunteering" and hits submit — calls `/api/letters/{id}/regenerate`. Shows the new version in place.

**DiscoveryResults** — Table of batch discovery results. Columns: Company, Score (0-100), Tier badge, Archetype label, Top Signal, Confidence indicator. Sortable and filterable by tier.

**AlignmentScoreBar** — Visual bar for 0-100 score. Shows 10 subcategory breakdown with mini bars. Color: green (PRIORITY 80+), blue (STRONG 60-79), yellow (POSSIBLE 40-59), gray (MONITOR 25-39), red (PASS <25). Tier badge and archetype label displayed.

**ProspectTable** — Sortable table with columns: Company logo (Clearbit), Name, Score (0-100), Tier badge, Archetype label, Status badge, Actions. Click row → navigate to `/prospects/[id]`.

**DossierCard** — Company dossier with 10-dimension score breakdown, archetype badge, outreach brief, matched programs, matched stories, contacts.

### Navigation

Navbar links: Dashboard (`/`), Discovery (`/discovery`), Research (`/research`)

## Coding Rules

### Python

- All DB operations are async. Use `AsyncSession` and `await session.execute(...)`.
- All FastAPI endpoints are `async def`.
- Use `Depends(get_db)` for DB session injection in routes.
- Pydantic v2 syntax throughout (`model_validator`, `field_validator`, not v1 style).
- Import settings: `from backend.config import settings` (never `os.environ`).
- Log with `import logging; logger = logging.getLogger(__name__)`.
- Handle Crawl4AI failures gracefully — wrap in try/except, return partial data rather than raising. Scraping failures should not abort the entire research job.

### httpx Usage

All httpx calls (PDF downloads, HTTP requests) must use `follow_redirects=True`:

```python
async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
    response = await client.get(url)
    response.raise_for_status()
```

Corporate sites frequently redirect PDF and CSR page URLs — always follow redirects silently.

### TypeScript / React

- No `any` types.
- Functional components only. No class components.
- `"use client"` only where needed (EventSource, useState, onClick handlers).
- Keep server components as the default — only add `"use client"` when required.
- All API response types must match the Pydantic schemas in `backend/models/schemas.py`.

### General

- No hardcoded strings for company names, model IDs, or config values. Everything goes through `config.py` or is passed as a parameter.
- Agent system prompts live in the agent file as a `CONSTANT_NAMED_STRING`, not inline in the Agent constructor call.
- Every Agno agent must have `structured_outputs=True` and a `response_model`.
- API fallbacks are mandatory — every external API call must have a fallback path.
- Researcher agent only runs on PRIORITY and STRONG tier companies — never on POSSIBLE, MONITOR, or PASS.
- Archetype (A-F) must flow through the entire pipeline: qualifier assigns it, researcher uses it for tone/angle, letter reflects it.
- Confidence flag (HIGH/MEDIUM/LOW) must be surfaced to the user in the UI, not hidden.

## How to Run

```bash
# 1. Start database (first time or after docker volume delete)
docker compose up -d
# Wait for healthy: docker compose ps

# 2. Backend (from project root)
cd backend
pip install -r requirements.txt
crawl4ai-setup          # ONE TIME: installs Playwright browsers
alembic upgrade head    # run migrations
uvicorn main:app --reload --port 8000

# 3. Frontend (new terminal, from project root)
cd frontend
npm install
npm run dev             # http://localhost:3000

# 4. Seed demo data (new terminal, optional but recommended for demo)
python seed/seed_demo_data.py

# 5. Verify
curl http://localhost:8000/health
# Should return: {"status": "ok", "service": "harlem-grown-prospect-intelligence"}
```

## Build Order

Follow this sequence. Do not skip ahead. Verify each phase before proceeding.

```
PHASE 1 — INFRASTRUCTURE
[ ] docker-compose.yml + backend/sql/init.sql
[ ] .env (with all vars including API keys)
[ ] backend/config.py (with new API vars)
[ ] backend/database.py
[ ] backend/models/orm.py (6 tables: prospects, dossiers, generated_letters, research_jobs, knowledge_chunks, discovery_jobs)
[ ] backend/models/schemas.py (discovery schemas, 10-dim QualificationResult, updated ProspectResponse with tier/archetype)
[ ] Alembic setup + initial migration
[ ] docker compose up -d && alembic upgrade head
✓ VERIFY: psql shows all 6 tables + vector extension

PHASE 2 — TOOLS
[ ] backend/tools/scraper.py
[ ] backend/tools/pdf_extractor.py
[ ] backend/tools/companies_api.py (The Companies API — firmographic queries)
[ ] backend/tools/donation_api.py (Double the Donation — volunteer/giving programs)
[ ] backend/tools/propublica_api.py (ProPublica — 990 data)
[ ] backend/tools/directory_scraper.py (B Corp + 1% for the Planet)
[ ] backend/tools/db_tools.py (with search_criteria_kb for sponsor framework)
[ ] seed/curated_seed_list.json (~100 NYC companies as API fallback)
✓ VERIFY: scrape_page("https://example.com") returns markdown string
✓ VERIFY: companies_api query returns NYC companies

PHASE 3 — RAG
[ ] knowledge_base/ — all 5 markdown files (including sponsor_criteria_framework.md)
[ ] backend/rag/loader.py (COLLECTION_MAP includes "criteria")
[ ] backend/rag/retriever.py
✓ VERIFY: load KB, similarity_search("youth farming programs", "programs", 3) returns results
✓ VERIFY: similarity_search("volunteer engagement", "criteria", 3) returns framework chunks

PHASE 4 — AGENTS
[ ] Pydantic response models (QualificationResult with 10 dims + tier + archetype, ResearchResult with outreach_brief + letter)
[ ] backend/agents/discovery.py (Haiku 4.5, tools: companies_api, bcorp_search, onepercentplanet_search)
[ ] backend/agents/qualifier.py (Haiku 4.5, 10 dimensions, archetype, tier, confidence — full rubric from framework in system prompt)
[ ] backend/agents/researcher.py (Sonnet 4.5, produces letter + outreach brief + RAG matching, uses archetype for tone)
[ ] backend/agents/team.py (2 agents: qualifier → researcher, tier gate between them)
✓ VERIFY: Run qualifier standalone on https://www.goldmansachs.com, returns score 0-100 with tier + archetype

PHASE 5 — API
[ ] backend/routers/prospects.py
[ ] backend/routers/research.py (with SSE stream — 2 steps: qualifier → researcher)
[ ] backend/routers/letters.py
[ ] backend/routers/discovery.py (4 endpoints: run, stream, results, research-batch)
[ ] backend/main.py (discovery router instead of chat router)
✓ VERIFY: uvicorn starts, http://localhost:8000/docs loads all routes

PHASE 6 — FRONTEND
[ ] Next.js scaffold + shadcn init + npm installs
[ ] frontend/lib/types.ts (with tier, archetype, 10-dim scores, discovery types)
[ ] frontend/lib/api.ts (discovery endpoints, no chat endpoints)
[ ] frontend/components/Navbar.tsx (Dashboard, Discovery, Research — no Chat)
[ ] frontend/components/ProspectTable.tsx (tier + archetype columns)
[ ] frontend/components/AlignmentScoreBar.tsx (0-100, 10 dims, tier badge, archetype)
[ ] frontend/app/page.tsx (dashboard)
[ ] frontend/components/AgentProgressStream.tsx (2 steps, not 4)
[ ] frontend/app/research/page.tsx
[ ] frontend/components/BatchProgressStream.tsx (3 steps for batch discovery)
[ ] frontend/components/DiscoveryResults.tsx
[ ] frontend/app/discovery/page.tsx
[ ] frontend/components/DossierCard.tsx (10-dim breakdown, archetype badge)
[ ] frontend/components/LetterEditor.tsx
[ ] frontend/app/prospects/[id]/page.tsx
✓ VERIFY: Full flow — add Goldman Sachs → qualifier scores → researcher runs → dossier + letter appear

PHASE 7 — SEED DATA
[ ] seed/curated_seed_list.json (~100 NYC companies)
[ ] seed/seed_demo_data.py (4 companies with 0-100 scores, tiers, archetypes, 10-dim breakdowns)
✓ VERIFY: Dashboard shows 4 prospects with 0-100 scores, tier badges, archetype labels
```

## Demo Script (What This Should Look Like When Done)

The demo supports two flows:

### Flow A: Batch Discovery

1. **Open Discovery page** — Click "Run Discovery" with default filters (NYC, target sectors, 200+ employees)
2. **Watch batch run** — BatchProgressStream shows 3 steps: Discovery (finding candidates), Qualifier (scoring batch), Researcher (deep-diving top companies)
3. **Browse results** — DiscoveryResults table shows 15-30 qualified companies sorted by score. Tier badges (PRIORITY in green, STRONG in blue). Archetype labels.
4. **Pick a PRIORITY company** — Click through to dossier. 10-dimension breakdown. Outreach brief. Draft letter.
5. **Rewrite letter** — Type "lead with the farm volunteer day angle" → new version in 10 seconds

### Flow B: Single-Company Live Research

1. **Dashboard** — Show the 4 pre-seeded prospects with alignment scores, tier badges, archetype labels
2. **Add new prospect** — Type a company name + URL on Research page
3. **Watch research run** — AgentProgressStream shows 2 steps completing in real time (Qualifier → Researcher)
4. **Open dossier** — Company logo, 10-dim score breakdown, archetype badge, matched HG programs
5. **Read the letter** — Point out how it mirrors the company's own values language and uses archetype-specific angle
6. **Rewrite it** — Type "make it lead with the volunteer day angle" → new version in 10 seconds

The killer demo moments: watching batch qualify dozens of companies in real time (Flow A, step 2) and live letter rewrite (both flows).

## Common Pitfalls — Avoid These

- Don't use `Base.metadata.create_all()` anywhere. Always Alembic.
- Don't use ChromaDB or any external vector store. pgvector is the only vector store.
- Don't use LangChain or LangGraph. Agno only for agent orchestration.
- Don't use Firecrawl. Crawl4AI only. It's free and local.
- Don't make Crawl4AI failures fatal. Wrap scraping in try/except. Return what you have.
- Don't block the SSE stream. Research runs in a background task — the SSE endpoint just polls the `research_jobs.step_log` column every 500ms.
- Don't embed with Anthropic. OpenAI `text-embedding-3-small` only for embeddings.
- Don't put config values in agent files. Import from `config.py`.
- Don't use synchronous SQLAlchemy anywhere in the backend. Async only. Exception: Alembic migration scripts use sync (this is correct and expected).
- Don't forget `follow_redirects=True` on httpx clients. Corporate PDF and CSR page URLs frequently redirect.
- Don't call external APIs without a fallback path. Every pipeline (A-D) must degrade gracefully.
- Don't run the Researcher agent on POSSIBLE, MONITOR, or PASS tier companies. Only PRIORITY and STRONG.
- Don't forget to pass archetype through the pipeline. Qualifier assigns it, Researcher uses it for letter tone.
- Don't hide the confidence flag. LOW confidence = thin CSR data = user should know.

## Known Limitations

1. **Pipeline B single point of failure** — Dimensions 1, 2, 3, 7 all come from the same CSR page crawl. A thin or missing page degrades 40% of the score simultaneously. Mitigated by confidence flag.
2. **Dimension 8 coverage** — Decision-maker accessibility has only ~50% automated coverage. Manual research fallback is acceptable for demo.
3. **Giving capacity is a proxy** — Dimension 6 uses revenue/headcount, not actual philanthropic spend. ProPublica 990 data can supplement when available.
4. **The Companies API credit limit** — Free tier is 500 credits. Sufficient for demo, needs paid plan for production.
5. **Double the Donation access** — Nonprofit-priced but requires API access approval. Build with fallback to web search.

## Reference Documents

| Document | When to Use |
|---|---|
| CLAUDE.md (this file) | Start of every session. Conventions + quick reference. |
| harlem_grown_prd.md | Deep detail on any component. Full code examples. Full DB schema. |
| sponsor_criteria_framework.md | 10 scoring dimensions with exact rubrics. Archetype profiles A-F. Search criteria. Qualifier system prompt source. |

When you're unsure about a pattern, check `harlem_grown_prd.md` Section 15 (Code Examples — Critical Patterns) first.
When you need the exact scoring rubric or archetype definitions, check `sponsor_criteria_framework.md` Parts 4-6.
