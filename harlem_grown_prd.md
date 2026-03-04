# Harlem Grown — Corporate Prospect Intelligence System
## Product Requirements Document (PRD)
### Version 1.0 | Hackathon Build Guide for Claude Code

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Prerequisites — Manual Installs & Accounts](#2-prerequisites--manual-installs--accounts)
3. [Environment Variables (.env)](#3-environment-variables-env)
4. [Complete File & Directory Structure](#4-complete-file--directory-structure)
5. [Database Schema](#5-database-schema)
6. [Knowledge Base Structure](#6-knowledge-base-structure)
7. [Backend — Agent Architecture](#7-backend--agent-architecture)
8. [Backend — Tools](#8-backend--tools)
9. [Backend — RAG Layer](#9-backend--rag-layer)
10. [Backend — API Routes](#10-backend--api-routes)
11. [Frontend Architecture](#11-frontend-architecture)
12. [Docker Setup](#12-docker-setup)
13. [Build Order for Claude Code](#13-build-order-for-claude-code)
14. [Demo Seed Data](#14-demo-seed-data)
15. [Code Examples — Critical Patterns](#15-code-examples--critical-patterns)

---

## 1. Project Overview

### What This System Does

A multi-agent AI system that helps Harlem Grown's small development team identify, research, and craft personalized outreach to corporate sponsors. Given a company name and URL, the system autonomously:

1. **Qualifies** whether the company is a strong mission-aligned prospect
2. **Researches** their ESG priorities, giving patterns, and decision-makers
3. **Matches** Harlem Grown programs and impact stories to the company's stated values
4. **Writes** a personalized briefing doc and introduction letter addressed to the right person
5. **Enables** the HG team to ask questions, refine letters, and strategize via a chat co-pilot

### Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Python 3.11 + FastAPI |
| Agent Framework | Agno (multi-agent teams) |
| LLM | Anthropic Claude (Sonnet 4.5 for reasoning, Haiku 3 for classification) |
| Database | PostgreSQL 16 + pgvector extension |
| ORM | SQLAlchemy 2.0 async + Alembic |
| Web Scraping | Crawl4AI (async, free, local) |
| PDF Extraction | PyMuPDF (fitz) |
| Embeddings | OpenAI text-embedding-3-small (1536 dimensions) |
| Frontend | Next.js 14 (App Router) + Tailwind CSS + shadcn/ui |
| Containerization | Docker Compose (Postgres only) |
| File Storage | Local filesystem ./storage/ |

---

## 2. Prerequisites — Manual Installs & Accounts

### System Requirements

Install these manually before running Claude Code:

```bash
# Python 3.11+
python --version  # must be 3.11 or higher

# Node.js 18+
node --version  # must be 18 or higher

# Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/

# Git
git --version
```

### Python Package Installs (backend)

Claude Code will generate requirements.txt — but run this to pre-verify pip is working:

```bash
pip install uv  # faster package manager, recommended
```

Full requirements.txt that Claude Code must create:

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

### Node Package Installs (frontend)

Claude Code will generate package.json. The key packages:

```bash
# Run inside /frontend directory
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card badge table tabs textarea dialog progress
npm install @tanstack/react-query axios eventsource-parser lucide-react recharts
```

### Accounts & API Keys Needed

| Service | Purpose | Where to Get |
|---|---|---|
| Anthropic | LLM for all agents | https://console.anthropic.com |
| OpenAI | text-embedding-3-small only | https://platform.openai.com |
| Docker Hub | Pull pgvector image | https://hub.docker.com (free account) |

> **Note:** Crawl4AI is fully local — no API key needed. No Firecrawl, no ChromaDB, no other external services required.

### One-Time Crawl4AI Setup

After pip install, run this once:

```bash
crawl4ai-setup  # installs Playwright browsers
python -c "import crawl4ai; print('Crawl4AI ready')"
```

---

## 3. Environment Variables (.env)

Create this file at the project root as `.env`:

```env
# ============================================
# ANTHROPIC — Required for all agents
# Get from: https://console.anthropic.com/settings/keys
# ============================================
ANTHROPIC_API_KEY=sk-ant-...

# ============================================
# OPENAI — Required for embeddings only
# Get from: https://platform.openai.com/api-keys
# ============================================
OPENAI_API_KEY=sk-...

# ============================================
# DATABASE — Matches docker-compose.yml
# No changes needed for local dev
# ============================================
DATABASE_URL=postgresql+asyncpg://hg_user:hg_password@localhost:5432/harlem_grown
DATABASE_URL_SYNC=postgresql://hg_user:hg_password@localhost:5432/harlem_grown

# ============================================
# STORAGE — Local filesystem paths
# ============================================
STORAGE_DIR=./backend/storage
KNOWLEDGE_BASE_DIR=./knowledge_base

# ============================================
# APP CONFIG
# ============================================
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
LOG_LEVEL=INFO

# ============================================
# EMBEDDING CONFIG
# ============================================
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
EMBEDDING_CHUNK_SIZE=500
EMBEDDING_CHUNK_OVERLAP=50
```

---

## 4. Complete File & Directory Structure

Claude Code must create every file and directory listed below:

```
harlem-grown-prospect/
│
├── .env                              # Environment variables (gitignored)
├── .gitignore
├── docker-compose.yml                # Postgres + pgvector
├── README.md
│
├── backend/
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Pydantic settings loader
│   ├── database.py                   # Async SQLAlchemy engine + session
│   │
│   ├── alembic.ini                   # Alembic migration config
│   ├── alembic/
│   │   ├── env.py                    # Alembic async env
│   │   └── versions/
│   │       └── 001_initial_schema.py # Initial migration (all tables)
│   │
│   ├── sql/
│   │   └── init.sql                  # CREATE EXTENSION vector;
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── orm.py                    # SQLAlchemy table definitions
│   │   └── schemas.py                # Pydantic request/response models
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── team.py                   # Agno Team orchestrator
│   │   ├── qualifier.py              # Agent: prospect qualification
│   │   ├── researcher.py             # Agent: deep ESG research
│   │   ├── narrative_matcher.py      # Agent: RAG-based story/program matching
│   │   ├── writer.py                 # Agent: letter + briefing generation
│   │   └── chat_agent.py             # Agent: HG team co-pilot
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── scraper.py                # Crawl4AI async wrappers
│   │   ├── pdf_extractor.py          # PyMuPDF PDF text extraction
│   │   └── db_tools.py               # Agent-callable DB query functions
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loader.py                 # Chunk + embed KB docs → pgvector
│   │   └── retriever.py              # pgvector cosine similarity search
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── prospects.py              # CRUD for prospects
│   │   ├── research.py               # Trigger research + SSE stream
│   │   ├── letters.py                # Letter retrieval + regeneration
│   │   └── chat.py                   # Chat agent streaming endpoint
│   │
│   └── storage/                      # Local file storage (gitignored contents)
│       ├── pdfs/                     # Downloaded ESG report PDFs
│       └── exports/                  # Exported letters + briefings
│
├── knowledge_base/
│   ├── harlem_grown_overview.md      # Mission, history, stats, founder
│   ├── programs.md                   # All programs with details + stats
│   ├── impact_stories.md             # Tagged emotional stories (8-10)
│   └── sponsorship_tiers.md          # Tier names, amounts, benefits
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   │
│   ├── app/
│   │   ├── layout.tsx                # Root layout + providers
│   │   ├── page.tsx                  # Dashboard (stats + prospect queue)
│   │   ├── globals.css
│   │   │
│   │   ├── prospects/
│   │   │   ├── page.tsx              # Prospect list view
│   │   │   └── [id]/
│   │   │       └── page.tsx          # Dossier + letter view
│   │   │
│   │   ├── research/
│   │   │   └── page.tsx              # Add prospect + run research
│   │   │
│   │   └── chat/
│   │       └── page.tsx              # Team co-pilot chat
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn/ui auto-generated
│   │   ├── AgentProgressStream.tsx   # Live SSE agent step visualization
│   │   ├── DossierCard.tsx           # Company dossier display
│   │   ├── LetterEditor.tsx          # Letter view + edit + regenerate
│   │   ├── ChatInterface.tsx         # Streaming chat component
│   │   ├── ProspectTable.tsx         # Sortable prospect queue table
│   │   ├── AlignmentScoreBar.tsx     # Visual score breakdown
│   │   └── Navbar.tsx                # App navigation
│   │
│   └── lib/
│       ├── api.ts                    # Typed API client (axios)
│       └── types.ts                  # Shared TypeScript types
│
└── seed/
    └── seed_demo_data.py             # Pre-load 4 demo prospects with dossiers
```

---

## 5. Database Schema

### PostgreSQL + pgvector Tables

Claude Code must implement all tables using SQLAlchemy 2.0 async ORM in `backend/models/orm.py`.

---

### Table: `prospects`

```sql
CREATE TABLE prospects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name    VARCHAR(255) NOT NULL,
    website_url     VARCHAR(512) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'queued',
                    -- ENUM: queued | qualifying | researching | complete | rejected | failed
    alignment_score FLOAT,             -- 0-60 total score, NULL until qualified
    alignment_breakdown JSONB,
    -- Example breakdown:
    -- {
    --   "youth_development": 8,
    --   "food_nutrition": 9,
    --   "environmental_sustainability": 7,
    --   "nyc_harlem_focus": 6,
    --   "workforce_development": 4,
    --   "employee_engagement": 7
    -- }
    go_no_go        BOOLEAN,           -- qualification decision
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prospects_status ON prospects(status);
CREATE INDEX idx_prospects_score ON prospects(alignment_score DESC);
```

---

### Table: `dossiers`

```sql
CREATE TABLE dossiers (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id          UUID REFERENCES prospects(id) ON DELETE CASCADE,
    company_summary      TEXT,          -- 3-sentence narrative summary
    esg_priorities       JSONB,
    -- Example:
    -- [
    --   {"priority": "Youth Education", "evidence": "Quote from their CSR page",
    --    "importance": "high"},
    --   {"priority": "Food Access", "evidence": "...", "importance": "medium"}
    -- ]
    giving_patterns      JSONB,
    -- Example:
    -- {
    --   "typical_range": "$25K-$100K",
    --   "preferred_types": ["program_sponsorship", "volunteer_days"],
    --   "past_partners": ["Robin Hood Foundation", "City Harvest"],
    --   "decision_timeline": "Q4 budget cycle"
    -- }
    csuite_contacts      JSONB,
    -- Example:
    -- [
    --   {
    --     "name": "Sarah Chen",
    --     "title": "VP Corporate Social Responsibility",
    --     "bio_snippet": "Former nonprofit director, Columbia MBA",
    --     "linkedin_url": "...",
    --     "is_primary_contact": true
    --   }
    -- ]
    matched_programs     JSONB,
    -- Example:
    -- [
    --   {"program_name": "School Partnerships",
    --    "relevance_reason": "Company prioritizes K-8 education",
    --    "relevance_score": 0.92,
    --    "suggested_angle": "Name a classroom at PS 175"},
    -- ]
    matched_stories      JSONB,
    -- Example:
    -- [
    --   {"story_title": "Marcus grows his first tomato",
    --    "tags": ["youth-transformation", "food-access"],
    --    "relevance_score": 0.88,
    --    "story_excerpt": "..."}
    -- ]
    raw_scraped_content  TEXT,          -- Full scraped text, stored for debugging
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dossiers_prospect ON dossiers(prospect_id);
```

---

### Table: `generated_letters`

```sql
CREATE TABLE generated_letters (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id             UUID REFERENCES prospects(id) ON DELETE CASCADE,
    version                 INTEGER NOT NULL DEFAULT 1,
    decision_maker_name     VARCHAR(255),
    decision_maker_title    VARCHAR(255),
    letter_body             TEXT NOT NULL,
    briefing_doc            TEXT NOT NULL,
    follow_up_path          JSONB,
    -- Example:
    -- [
    --   {"step": 1, "action": "Send intro letter", "timing": "Day 0"},
    --   {"step": 2, "action": "Follow-up if no response", "timing": "Day 7",
    --    "template": "Just following up on my note last week..."},
    --   {"step": 3, "action": "Invite to farm site visit", "timing": "Day 14"}
    -- ]
    generation_instructions TEXT,      -- What user asked for on rewrites
    is_current              BOOLEAN DEFAULT TRUE,  -- only one current per prospect
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_letters_prospect ON generated_letters(prospect_id);
CREATE INDEX idx_letters_current ON generated_letters(prospect_id, is_current);
```

---

### Table: `research_jobs`

```sql
CREATE TABLE research_jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id  UUID REFERENCES prospects(id) ON DELETE CASCADE,
    status       VARCHAR(50) NOT NULL DEFAULT 'pending',
                 -- ENUM: pending | running | complete | failed
    current_step VARCHAR(100),
    step_log     JSONB DEFAULT '[]'::jsonb,
    -- Array of step events:
    -- [
    --   {"step": "qualifier", "status": "complete",
    --    "message": "Qualified: score 38/60", "timestamp": "..."},
    --   {"step": "researcher", "status": "running",
    --    "message": "Scraping ESG report...", "timestamp": "..."}
    -- ]
    error_message TEXT,
    started_at   TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_jobs_prospect ON research_jobs(prospect_id);
CREATE INDEX idx_jobs_status ON research_jobs(status);
```

---

### Table: `knowledge_chunks` (RAG / pgvector)

```sql
CREATE TABLE knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_source  VARCHAR(255) NOT NULL,   -- filename, e.g. 'programs.md'
    collection  VARCHAR(100) NOT NULL,   -- 'programs' | 'stories' | 'overview' | 'tiers'
    chunk_text  TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,        -- position within source doc
    metadata    JSONB DEFAULT '{}'::jsonb,
    -- Example: {"tags": ["#youth-transformation"], "program_name": "Summer Camp"}
    embedding   vector(1536),           -- text-embedding-3-small output
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_collection ON knowledge_chunks(collection);

-- pgvector HNSW index for fast similarity search
CREATE INDEX idx_chunks_embedding
    ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

### Table: `chat_messages`

```sql
CREATE TABLE chat_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  VARCHAR(100) NOT NULL,
    role        VARCHAR(20) NOT NULL,   -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_session ON chat_messages(session_id, created_at);
```

---

### SQLAlchemy ORM (backend/models/orm.py)

```python
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMPTZ
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector
import uuid

class Base(DeclarativeBase):
    pass

class Prospect(Base):
    __tablename__ = "prospects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    website_url = Column(String(512), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    alignment_score = Column(Float, nullable=True)
    alignment_breakdown = Column(JSONB, nullable=True)
    go_no_go = Column(Boolean, nullable=True)
    created_at = Column(TIMESTAMPTZ, server_default="NOW()")
    updated_at = Column(TIMESTAMPTZ, server_default="NOW()", onupdate="NOW()")
    dossier = relationship("Dossier", back_populates="prospect", uselist=False)
    letters = relationship("GeneratedLetter", back_populates="prospect")
    jobs = relationship("ResearchJob", back_populates="prospect")

class Dossier(Base):
    __tablename__ = "dossiers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"))
    company_summary = Column(Text)
    esg_priorities = Column(JSONB)
    giving_patterns = Column(JSONB)
    csuite_contacts = Column(JSONB)
    matched_programs = Column(JSONB)
    matched_stories = Column(JSONB)
    raw_scraped_content = Column(Text)
    created_at = Column(TIMESTAMPTZ, server_default="NOW()")
    prospect = relationship("Prospect", back_populates="dossier")

class GeneratedLetter(Base):
    __tablename__ = "generated_letters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"))
    version = Column(Integer, default=1)
    decision_maker_name = Column(String(255))
    decision_maker_title = Column(String(255))
    letter_body = Column(Text, nullable=False)
    briefing_doc = Column(Text, nullable=False)
    follow_up_path = Column(JSONB)
    generation_instructions = Column(Text)
    is_current = Column(Boolean, default=True)
    created_at = Column(TIMESTAMPTZ, server_default="NOW()")
    prospect = relationship("Prospect", back_populates="letters")

class ResearchJob(Base):
    __tablename__ = "research_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"))
    status = Column(String(50), default="pending")
    current_step = Column(String(100))
    step_log = Column(JSONB, default=list)
    error_message = Column(Text)
    started_at = Column(TIMESTAMPTZ, server_default="NOW()")
    completed_at = Column(TIMESTAMPTZ)
    prospect = relationship("Prospect", back_populates="jobs")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_source = Column(String(255), nullable=False)
    collection = Column(String(100), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    metadata = Column(JSONB, default=dict)
    embedding = Column(Vector(1536))
    created_at = Column(TIMESTAMPTZ, server_default="NOW()")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMPTZ, server_default="NOW()")
```

---

## 6. Knowledge Base Structure

### Files in `/knowledge_base/`

Claude Code must create these stub files. Fill in real content from Harlem Grown's website and annual report before the demo.

---

### `knowledge_base/harlem_grown_overview.md`

```markdown
# Harlem Grown — Organization Overview

## Mission
To inspire youth to lead healthy and ambitious lives through mentorship
and hands-on education in urban farming, sustainability, and nutrition.

## Founded
2011 by Tony Hillery with one school partnership and one urban farm
in Central Harlem.

## Scale (Current)
- 14 urban agriculture facilities (soil farms, hydroponic greenhouses,
  school gardens, mushroom chamber)
- 18,000+ youth served annually
- 40+ staff, 5,000+ volunteers
- Located 122nd–152nd Streets, Central Harlem, Manhattan
- $5M+ annual fundraising goal

## Programs Overview
[Detail each program — see programs.md]

## Key Stats for Pitching
- 90% of kids who grow it try a new vegetable for the first time
- 80% want to eat that vegetable again
- Free programming for all participants
- Produce distributed free to community members weekly

## Founder Story
Tony Hillery started Harlem Grown after volunteering at a local school
and seeing children who had never seen a vegetable grow. He transformed
abandoned lots into thriving farms. Today the organization is a
cornerstone of Central Harlem.

## Funding Sources
Individuals, private foundations, corporate partners, local government.
Corporate sponsors are a key growth priority.
```

---

### `knowledge_base/programs.md`

```markdown
# Harlem Grown Programs

## 1. School Partnerships (Intensive)
[Fill with details: 6 partner schools, what a mentor-in-residence does,
hours per week, student outcomes, sponsor naming opportunities]

## 2. Summer Camp
[7-week intensive, 30 youth per cohort, free, farm-based curriculum,
nutrition education, cooking, what sponsors can fund]

## 3. Saturday Leadership Program
[20 students, leadership development, farm work, community service,
April–October]

## 4. Farm Tours & Workshops
[Dozens of schools annually, free, available for corporate group visits,
60-90 min format]

## 5. Workforce Development
[At-risk emerging adults, job training, agricultural skills,
employment placement]

## 6. Community Food Distribution
[Weekly fresh produce distribution, thousands of pounds annually,
free to community members, volunteer opportunities]

## 7. Mobile Teaching Kitchen
[Travels throughout Harlem, nutrition education, cooking demos,
reaches families who cannot come to farms]
```

---

### `knowledge_base/impact_stories.md`

```markdown
# Harlem Grown Impact Stories

Stories are tagged for matching to corporate sponsor values.
Tags: #youth-transformation #food-access #community #sustainability
      #workforce #leadership #family-impact #environment

---

## Story: [Title — e.g. "Marcus and the First Tomato"]
Tags: #youth-transformation #food-access
[150-200 word story about a specific child's transformation.
Pull from real Harlem Grown materials, social media, annual report.
Be specific: child's first name, age, before/after, emotional moment.]

---

## Story: [Title]
Tags: #community #family-impact
[Story about a family, community member, or neighborhood impact]

---
[Add 8-10 total stories covering different program areas and themes]
```

---

### `knowledge_base/sponsorship_tiers.md`

```markdown
# Harlem Grown Sponsorship Tiers

## Platinum Partner — $100,000+
- Program naming rights (one school partnership)
- Annual gala presenting sponsor
- 4 corporate volunteer days (up to 50 staff each)
- Quarterly impact reports
- Co-branded communications
- CEO recognition at all major events
- Farm naming opportunity

## Gold Partner — $50,000
- Named sponsor of Summer Camp cohort
- 2 corporate volunteer days (up to 30 staff)
- Semi-annual impact reports
- Gala table (10 seats)
- Co-branded social media features

## Silver Partner — $25,000
- Named sponsor of Saturday Leadership Program
- 1 corporate volunteer day (up to 20 staff)
- Annual impact report
- 4 gala tickets
- Website + newsletter recognition

## Community Partner — $10,000
- Named sponsor of a farm site for 1 year
- 1 group farm tour + harvest experience
- 2 gala tickets
- Social media recognition

## First Step — Site Visit (No commitment)
Recommended first engagement for new prospects.
A 90-minute farm tour for 6-10 corporate decision-makers.
Includes student presentations, harvest, and farm-to-table lunch.
Conversion rate to partnership: approximately 70%.
```

---

## 7. Backend — Agent Architecture

### Agent Team Orchestration (backend/agents/team.py)

```python
from agno.team import Team
from agno.agent import Agent
from agno.models.anthropic import Claude
from .qualifier import create_qualifier_agent
from .researcher import create_researcher_agent
from .narrative_matcher import create_narrative_matcher_agent
from .writer import create_writer_agent

def create_research_team() -> Team:
    """
    Sequential Agno Team. Each agent receives prior agent's output
    in the shared session state and appends its own structured output.
    """
    return Team(
        name="Harlem Grown Prospect Research Team",
        mode="sequential",
        model=Claude(id="claude-sonnet-4-5"),
        agents=[
            create_qualifier_agent(),
            create_researcher_agent(),
            create_narrative_matcher_agent(),
            create_writer_agent(),
        ],
        show_progress=True,
        enable_team_context=True,
        description=(
            "A multi-agent team that researches corporate prospects for Harlem Grown "
            "and produces personalized sponsorship outreach materials."
        ),
    )
```

---

### Qualifier Agent (backend/agents/qualifier.py)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import BaseModel
from typing import Optional
from ..tools.scraper import scrape_page, scrape_site

class QualificationResult(BaseModel):
    company_name: str
    website_url: str
    scores: dict  # keys: youth_development, food_nutrition,
                  # environmental_sustainability, nyc_harlem_focus,
                  # workforce_development, employee_engagement (each 0-10)
    total_score: float
    key_signals: list[str]      # Evidence quotes from their site
    go_no_go: bool              # True if total_score >= 25
    rejection_reason: Optional[str]

QUALIFIER_INSTRUCTIONS = """
You are a nonprofit prospect researcher evaluating whether companies are
strong sponsorship candidates for Harlem Grown.

ABOUT HARLEM GROWN:
Harlem Grown is a New York City nonprofit that operates 14 urban farms
in Central Harlem, serving 18,000+ youth annually through hands-on
education in urban farming, nutrition, and sustainability. Their programs
target K-12 students and young adults, focusing on food justice, healthy
living, and community empowerment.

YOUR JOB:
Given a company's name and website, scrape their CSR/sustainability page,
about page, and any giving/community pages. Score their alignment with
Harlem Grown across 6 dimensions (0-10 each):

1. YOUTH DEVELOPMENT (0-10): Do they fund youth education, after-school,
   mentorship, or K-12 programs?
2. FOOD & NUTRITION (0-10): Do they have any focus on food access,
   nutrition, healthy eating, or food equity?
3. ENVIRONMENTAL SUSTAINABILITY (0-10): Do they fund urban agriculture,
   green initiatives, climate, or environmental education?
4. NYC/HARLEM COMMUNITY FOCUS (0-10): Do they prioritize NYC communities,
   underserved neighborhoods, or Harlem specifically?
5. WORKFORCE DEVELOPMENT (0-10): Do they fund job training, at-risk youth
   employment, or workforce readiness programs?
6. EMPLOYEE ENGAGEMENT (0-10): Do they have active volunteer programs or
   seek hands-on partner experiences for employees?

SCORING RUBRIC:
- 0: No evidence whatsoever
- 3: Tangential mention
- 6: Clear stated priority
- 8: Active programs in this area
- 10: Core mission alignment with specific Harlem/NYC evidence

GO/NO-GO: Recommend GO if total_score >= 25/60.

IMPORTANT: Extract verbatim quotes from their website as key_signals.
These prove you read their actual content and will be used in
personalized outreach.
"""

def create_qualifier_agent() -> Agent:
    return Agent(
        name="Qualifier",
        description="Scores corporate prospect alignment with Harlem Grown's mission",
        model=Claude(id="claude-haiku-3"),   # cheaper, faster for this task
        tools=[scrape_page, scrape_site],
        response_model=QualificationResult,
        instructions=QUALIFIER_INSTRUCTIONS,
        structured_outputs=True,
    )
```

---

### Researcher Agent (backend/agents/researcher.py)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import BaseModel
from ..tools.scraper import scrape_page, scrape_site
from ..tools.pdf_extractor import extract_pdf_from_url

class ESGPriority(BaseModel):
    priority: str
    evidence: str       # verbatim quote from their materials
    importance: str     # high | medium | low

class CsuiteContact(BaseModel):
    name: str
    title: str
    bio_snippet: Optional[str]
    is_primary_contact: bool
    contact_rationale: str  # why this person owns the sponsorship decision

class GivingPatterns(BaseModel):
    typical_range: str
    preferred_engagement_types: list[str]
    past_nonprofit_partners: list[str]
    decision_timeline: str
    value_language: str  # exact phrases they use about their giving mission

class ResearchResult(BaseModel):
    company_summary: str            # 3-sentence narrative
    esg_priorities: list[ESGPriority]
    csuite_contacts: list[CsuiteContact]
    giving_patterns: GivingPatterns
    brand_voice: str                # formal | conversational | mission-driven | etc.
    raw_content_summary: str

RESEARCHER_INSTRUCTIONS = """
You are a deep-research analyst building a corporate intelligence dossier
for Harlem Grown's development team.

YOUR JOB:
Given a qualified company, scrape their full digital footprint to extract:

1. COMPANY SUMMARY: Write a 3-sentence summary of who they are, their
   core business, and their community/giving identity.

2. ESG PRIORITIES: Extract their top 4-6 ESG/CSR priorities with
   VERBATIM evidence quotes. The exact language they use to describe
   their values is gold — the writer agent will mirror it back.

3. C-SUITE CONTACTS: Find the leadership team page. Identify the 1-2
   people most likely to own the corporate sponsorship decision.
   Priority titles: VP/Director Corporate Social Responsibility, Chief
   People Officer, VP Community Affairs, Foundation Director,
   VP Partnerships, ESG Director.
   Include any humanizing bio details (alma mater, prior nonprofit work,
   personal philanthropic interests if public).

4. GIVING PATTERNS: Research press releases and news for evidence of
   past giving. What dollar ranges appear? What program types? What
   types of organizations do they favor? Do they prefer hands-on
   volunteer engagement or pure financial support?

5. BRAND VOICE: What is their communication style? Formal corporate,
   mission-driven, casual tech, etc.?

SCRAPING PRIORITIES:
- Homepage, About, Leadership/Team page
- CSR/Sustainability/Community/Giving/Foundation page
- Press releases mentioning: donation, grant, partnership, sponsor,
  foundation, community, giving (filter last 2 years)
- ESG report PDF if accessible

Be exhaustive. This dossier is the foundation for a personalized letter
that needs to feel like it was written by someone who spent a week
reading everything about this company.
"""

def create_researcher_agent() -> Agent:
    return Agent(
        name="Researcher",
        description="Extracts ESG priorities, giving patterns, and C-suite contacts",
        model=Claude(id="claude-sonnet-4-5"),
        tools=[scrape_page, scrape_site, extract_pdf_from_url],
        response_model=ResearchResult,
        instructions=RESEARCHER_INSTRUCTIONS,
        structured_outputs=True,
    )
```

---

### Narrative Matcher Agent (backend/agents/narrative_matcher.py)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import BaseModel
from ..tools.db_tools import search_programs_kb, search_stories_kb

class MatchedProgram(BaseModel):
    program_name: str
    relevance_reason: str
    relevance_score: float
    suggested_angle: str        # Specific pitch angle for this company
    sponsorship_tier: str       # Which tier fits this program

class MatchedStory(BaseModel):
    story_title: str
    tags: list[str]
    relevance_score: float
    story_excerpt: str
    why_it_resonates: str       # Why this story works for this company

class RecommendedFirstAsk(BaseModel):
    ask_type: str               # site_visit | volunteer_day | program_sponsor
    rationale: str
    suggested_script: str       # One-sentence suggested first ask

class NarrativeMatchResult(BaseModel):
    top_programs: list[MatchedProgram]     # Max 3
    top_stories: list[MatchedStory]        # Max 3
    recommended_tier: str
    recommended_ask_amount: str
    first_ask: RecommendedFirstAsk
    lead_angle: str             # The single strongest pitch angle for this company

MATCHER_INSTRUCTIONS = """
You are a storytelling strategist matching Harlem Grown's programs and
impact stories to a specific corporate prospect's values.

YOUR JOB:
Given a company's ESG priorities and giving patterns, use the provided
search tools to find the Harlem Grown programs and stories that will
resonate most with this specific company.

SEARCH STRATEGY:
- Search programs_kb with each of the company's top ESG priorities
  as search queries
- Search stories_kb for stories tagged with themes that match their values
- Score and rank results by true resonance — not just keyword overlap

MATCHING PRINCIPLES:
1. A sustainability-focused company should see the urban farming and
   composting angles most prominently
2. A financial services firm should see workforce development and
   economic mobility
3. A food/beverage company should see produce distribution and nutrition
4. A tech company should see the STEM + sustainability education angle
5. A healthcare company should see the nutrition and wellness outcomes

RECOMMENDED TIER:
Based on their estimated giving capacity from the giving_patterns data,
recommend the most appropriate sponsorship tier. Be conservative — it's
better to under-ask and upsell than to over-ask and lose the prospect.

FIRST ASK PRINCIPLE:
The best corporate partnerships start with an experience, not a check.
Unless the company clearly makes direct financial asks from cold outreach
(rare), recommend a site visit or volunteer day as the first ask.
A 90-minute farm tour has approximately 70% conversion to partnership.
"""

def create_narrative_matcher_agent() -> Agent:
    return Agent(
        name="NarrativeMatcher",
        description="Matches company ESG priorities to Harlem Grown programs and stories",
        model=Claude(id="claude-sonnet-4-5"),
        tools=[search_programs_kb, search_stories_kb],
        response_model=NarrativeMatchResult,
        instructions=MATCHER_INSTRUCTIONS,
        structured_outputs=True,
    )
```

---

### Writer Agent (backend/agents/writer.py)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import BaseModel

class FollowUpStep(BaseModel):
    step: int
    action: str
    timing: str
    template: Optional[str]

class WriterOutput(BaseModel):
    briefing_doc: str       # Markdown formatted staff briefing
    letter_body: str        # The actual introduction letter
    follow_up_path: list[FollowUpStep]
    letter_word_count: int

WRITER_INSTRUCTIONS = """
You are an expert nonprofit development writer crafting personalized
corporate sponsorship outreach for Harlem Grown.

You will receive a complete intelligence package including:
- Company summary and ESG priorities (with their exact language)
- Giving patterns and estimated capacity
- C-suite contact details
- Matched programs and impact stories
- Recommended first ask

PRODUCE THREE OUTPUTS:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT 1: STAFF BRIEFING DOC (Markdown)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format as a clean markdown document with these sections:

## Company at a Glance
[3-sentence summary, not their Wikipedia page — their giving identity]

## Why They're a Strong Match
[Specific evidence: score, key alignment signals, verbatim quotes
from their materials that show they care about what HG does]

## Who You're Talking To
[Decision-maker name, title, humanizing detail if available,
what they likely care about personally]

## The Angle to Lead With
[Single strongest pitch angle. Be specific.]

## Programs to Mention
[The 2-3 matched programs, why each resonates for this company]

## Stories to Tell
[2-3 impact stories to reference. Include why each one will land.]

## The Ask
[Recommended tier, dollar range, and first ask framing]

## What to Avoid
[Any sensitivities, misalignments, or topics to steer away from]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT 2: INTRODUCTION LETTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES:
- Maximum 350 words
- Address to the specific decision-maker by first name
- NEVER open with "I am writing to..." or "On behalf of..."
- Opening paragraph: Reference something specific about THEIR company
  or a recent initiative — not generic flattery. Show you did homework.
- Second paragraph: Introduce Harlem Grown through THEIR lens.
  Use their own values language. If they say "resilient communities,"
  use that phrase. If they talk about "systemic change," use that.
  Do NOT use HG's standard boilerplate.
- Third paragraph: A single modest ask — the site visit or volunteer
  day. Make it easy to say yes. Not "would you consider a $50,000
  sponsorship" — that's for the second meeting.
- Closing: Warm, specific, human. Reference something concrete.
- Sign from: [Harlem Grown Development Team will customize name]
- TONE: Mirror the company's brand voice. Formal for finance/law.
  Conversational for tech. Mission-driven for healthcare/food.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT 3: FOLLOW-UP PATH (3 steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: The initial letter (Day 0)
Step 2: Follow-up if no response (Day 7-10) — include a brief
        email template
Step 3: Escalation or alternative ask (Day 14-21)
"""

def create_writer_agent() -> Agent:
    return Agent(
        name="Writer",
        description="Generates personalized briefing doc, introduction letter, and follow-up path",
        model=Claude(id="claude-sonnet-4-5"),
        response_model=WriterOutput,
        instructions=WRITER_INSTRUCTIONS,
        structured_outputs=True,
    )
```

---

### Chat Co-pilot Agent (backend/agents/chat_agent.py)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.memory.db.postgres import PostgresMemory
from ..tools.db_tools import (
    get_all_prospects, get_dossier_by_company,
    get_letter_by_company, search_programs_kb, search_stories_kb
)

CHAT_AGENT_INSTRUCTIONS = """
You are the Corporate Partnership Strategist for Harlem Grown, a NYC
nonprofit that operates 14 urban farms serving 18,000+ youth annually.

You have deep knowledge of:
- All Harlem Grown programs (school partnerships, summer camp, Saturday
  program, farm tours, workforce development, food distribution)
- The organization's mission, impact stories, and sponsorship tiers
- All researched corporate prospects and their dossiers
- Generated outreach letters and their status

YOUR ROLE is to help Harlem Grown's small development team work smarter.
You can:
- Surface the best prospects to prioritize this week
- Explain why a specific company is or isn't a good fit
- Rewrite or refine any generated letter on request
- Suggest which programs or stories to emphasize for a given company type
- Answer questions about HG programs and impact data
- Help prepare talking points for a specific upcoming call

TONE: You are a strategic advisor who deeply cares about HG's mission.
Be direct, specific, and actionable. Never vague. If asked to rewrite
a letter, actually rewrite it — don't just describe what should change.

EXAMPLE REQUESTS YOU HANDLE WELL:
- "Who should we call this week?" → Surface top scored prospects
- "Rewrite the Goldman letter to lead with volunteering"
- "What's the best angle for a pharma company?"
- "What impact stats should I mention in a call with a food brand?"
- "Draft a follow-up for someone who saw the farm but hasn't committed"
"""

def create_chat_agent(db_url: str) -> Agent:
    return Agent(
        name="HarlemGrownPartnershipStrategist",
        model=Claude(id="claude-sonnet-4-5"),
        tools=[
            get_all_prospects,
            get_dossier_by_company,
            get_letter_by_company,
            search_programs_kb,
            search_stories_kb,
        ],
        memory=PostgresMemory(
            db_url=db_url,
            table_name="chat_messages",
        ),
        instructions=CHAT_AGENT_INSTRUCTIONS,
        stream=True,
    )
```

---

## 8. Backend — Tools

### Scraper (backend/tools/scraper.py)

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import NoExtractionStrategy

# Target page keywords for site crawl
CSR_KEYWORDS = [
    "csr", "sustainability", "community", "giving", "responsibility",
    "foundation", "social-impact", "esg", "environment", "partnership",
    "volunteer", "nonprofit", "grant", "philanthrop"
]

async def scrape_page(url: str) -> str:
    """
    Scrape a single URL. Returns clean markdown suitable for LLM input.
    Strips navigation, ads, boilerplate.
    Tool docstring used by Agno for agent tool descriptions.
    """
    config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,     # cache for dev speed
        word_count_threshold=50,          # skip thin pages
        remove_overlay_elements=True,
        process_iframes=False,
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        if result.success:
            return result.markdown_v2.fit_markdown or result.markdown
        return f"[Scrape failed for {url}: {result.error_message}]"


async def scrape_site(base_url: str, max_pages: int = 8) -> list[dict]:
    """
    Crawl a company website. Targets pages likely to contain CSR/ESG content.
    Returns list of {url, title, content} dicts.
    Prioritizes pages with CSR_KEYWORDS in URL path or page title.
    """
    from urllib.parse import urljoin, urlparse
    import httpx

    # First get sitemap or homepage links
    home_content = await scrape_page(base_url)

    # Extract internal links from homepage
    # Crawl4AI provides links in result.links
    config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=base_url, config=config)
        links = result.links.get("internal", [])

    # Score links by keyword presence
    def score_link(link: dict) -> int:
        href = link.get("href", "").lower()
        text = link.get("text", "").lower()
        return sum(1 for kw in CSR_KEYWORDS if kw in href or kw in text)

    scored = sorted(links, key=score_link, reverse=True)
    priority_urls = [base_url] + [l["href"] for l in scored[:max_pages-1]]

    # Scrape all priority pages
    pages = []
    for url in priority_urls:
        content = await scrape_page(url)
        if len(content) > 200:  # skip empty pages
            pages.append({"url": url, "content": content})

    return pages


async def find_esg_report_url(company_website: str) -> str | None:
    """
    Attempt to find a company's ESG/CSR/Sustainability report PDF URL.
    Searches common URL patterns and page links.
    Returns URL string if found, None otherwise.
    """
    common_paths = [
        "/sustainability", "/csr", "/esg", "/responsibility",
        "/corporate-responsibility", "/impact", "/environment",
        "/annual-report", "/foundation"
    ]
    # Check each path, look for PDF links in content
    ...
```

---

### PDF Extractor (backend/tools/pdf_extractor.py)

```python
import fitz  # PyMuPDF
import httpx
import os
from pathlib import Path
from ..config import settings

async def extract_pdf_from_url(url: str) -> str:
    """
    Download a PDF from URL, save locally, extract text.
    Returns extracted text (first 50,000 chars to stay within context).
    Saves to ./storage/pdfs/ for reference.
    """
    storage_path = Path(settings.STORAGE_DIR) / "pdfs"
    storage_path.mkdir(parents=True, exist_ok=True)

    # Download
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    # Save file
    filename = url.split("/")[-1] or "report.pdf"
    filepath = storage_path / filename
    filepath.write_bytes(response.content)

    # Extract text
    doc = fitz.open(str(filepath))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()

    full_text = "\n".join(text_parts)
    # Return first 50K chars — enough for LLM context
    return full_text[:50000]
```

---

### DB Tools for Agents (backend/tools/db_tools.py)

```python
"""
Agent-callable tools that query the database.
These are regular async Python functions — Agno wraps them as tools
via the @tool decorator or by passing them directly to Agent(tools=[...]).
Docstrings are used by the LLM to understand when to call each tool.
"""

from sqlalchemy import select, desc
from ..database import AsyncSessionLocal
from ..models.orm import Prospect, Dossier, GeneratedLetter
from ..rag.retriever import similarity_search

async def get_all_prospects(limit: int = 20) -> list[dict]:
    """
    Get all prospects with their status, alignment score, and whether
    a letter has been generated. Use this to show the team which
    prospects are ready to contact.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prospect)
            .order_by(desc(Prospect.alignment_score))
            .limit(limit)
        )
        prospects = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "company_name": p.company_name,
                "status": p.status,
                "alignment_score": p.alignment_score,
                "website_url": p.website_url,
            }
            for p in prospects
        ]


async def get_dossier_by_company(company_name: str) -> dict | None:
    """
    Get the full intelligence dossier for a specific company by name.
    Returns ESG priorities, giving patterns, contacts, and matched programs.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prospect).where(
                Prospect.company_name.ilike(f"%{company_name}%")
            )
        )
        prospect = result.scalar_one_or_none()
        if not prospect or not prospect.dossier:
            return None
        d = prospect.dossier
        return {
            "company_summary": d.company_summary,
            "esg_priorities": d.esg_priorities,
            "giving_patterns": d.giving_patterns,
            "csuite_contacts": d.csuite_contacts,
            "matched_programs": d.matched_programs,
            "matched_stories": d.matched_stories,
        }


async def get_letter_by_company(company_name: str) -> dict | None:
    """
    Get the current generated letter and briefing doc for a company.
    Returns the letter body and staff briefing document.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prospect).where(
                Prospect.company_name.ilike(f"%{company_name}%")
            )
        )
        prospect = result.scalar_one_or_none()
        if not prospect:
            return None
        current_letters = [l for l in prospect.letters if l.is_current]
        if not current_letters:
            return None
        letter = current_letters[0]
        return {
            "letter_body": letter.letter_body,
            "briefing_doc": letter.briefing_doc,
            "decision_maker_name": letter.decision_maker_name,
            "version": letter.version,
        }


async def search_programs_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Search Harlem Grown's program knowledge base using semantic similarity.
    Use this when you need to find which HG programs best match a
    company's interests or ESG priorities.
    """
    return await similarity_search(query=query, collection="programs", top_k=top_k)


async def search_stories_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Search Harlem Grown's impact story library using semantic similarity.
    Use this to find emotional stories that will resonate with a specific
    company's values or stated priorities.
    """
    return await similarity_search(query=query, collection="stories", top_k=top_k)
```

---

## 9. Backend — RAG Layer

### Knowledge Base Loader (backend/rag/loader.py)

```python
import os
import tiktoken
from pathlib import Path
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.orm import KnowledgeChunk
from ..config import settings

openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
tokenizer = tiktoken.get_encoding("cl100k_base")

COLLECTION_MAP = {
    "programs": "programs",
    "impact_stories": "stories",
    "harlem_grown_overview": "overview",
    "sponsorship_tiers": "tiers",
}

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Token-aware chunking with overlap."""
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(tokenizer.decode(chunk_tokens))
        start += chunk_size - overlap
    return chunks


async def get_embedding(text: str) -> list[float]:
    """Get embedding from OpenAI text-embedding-3-small."""
    response = await openai.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text.replace("\n", " "),
    )
    return response.data[0].embedding


async def load_knowledge_base(session: AsyncSession, force_reload: bool = False):
    """
    Load all markdown files from knowledge_base/ into pgvector.
    Skips if already loaded (unless force_reload=True).
    """
    kb_path = Path(settings.KNOWLEDGE_BASE_DIR)

    for md_file in kb_path.glob("*.md"):
        # Determine collection from filename
        stem = md_file.stem.lower().replace("-", "_")
        collection = None
        for key, val in COLLECTION_MAP.items():
            if key in stem:
                collection = val
                break
        if not collection:
            collection = "general"

        content = md_file.read_text(encoding="utf-8")
        chunks = chunk_text(content)

        for i, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)
            session.add(KnowledgeChunk(
                doc_source=md_file.name,
                collection=collection,
                chunk_text=chunk,
                chunk_index=i,
                embedding=embedding,
            ))

    await session.commit()
    print(f"Knowledge base loaded: {len(list(kb_path.glob('*.md')))} files")
```

---

### Retriever (backend/rag/retriever.py)

```python
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from ..database import AsyncSessionLocal
from ..models.orm import KnowledgeChunk
from ..config import settings

openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def similarity_search(
    query: str,
    collection: str,
    top_k: int = 3
) -> list[dict]:
    """
    Cosine similarity search against pgvector.
    Returns top_k most similar chunks with their text and score.
    """
    # Get query embedding
    response = await openai.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=query.replace("\n", " "),
    )
    query_embedding = response.data[0].embedding

    async with AsyncSessionLocal() as session:
        # pgvector cosine distance operator: <=>
        result = await session.execute(
            text("""
                SELECT
                    chunk_text,
                    doc_source,
                    metadata,
                    1 - (embedding <=> :embedding::vector) AS similarity
                FROM knowledge_chunks
                WHERE collection = :collection
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """),
            {
                "embedding": str(query_embedding),
                "collection": collection,
                "top_k": top_k
            }
        )
        rows = result.fetchall()

    return [
        {
            "chunk_text": row.chunk_text,
            "doc_source": row.doc_source,
            "metadata": row.metadata,
            "similarity_score": float(row.similarity),
        }
        for row in rows
    ]
```

---

## 10. Backend — API Routes

### Research Route with SSE Streaming (backend/routers/research.py)

```python
import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.orm import Prospect, ResearchJob
from ..agents.team import create_research_team

router = APIRouter(prefix="/api/research", tags=["research"])

@router.post("/{prospect_id}/run")
async def run_research(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger the research agent team for a prospect."""
    # Create job record
    job = ResearchJob(prospect_id=prospect_id, status="running")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Run in background (don't await — let SSE stream do it)
    asyncio.create_task(
        _run_research_task(str(job.id), prospect_id, db)
    )
    return {"job_id": str(job.id)}


@router.get("/stream/{job_id}")
async def stream_research_progress(job_id: str):
    """
    SSE endpoint. Frontend connects here to see live agent progress.
    Events emitted: step_start, step_complete, step_error, job_complete
    """
    async def event_generator():
        # Poll job status from DB every 500ms
        # In production, use Redis pub/sub. For hackathon, polling is fine.
        last_step_count = 0
        max_polls = 300  # 2.5 minutes timeout

        for _ in range(max_polls):
            async with AsyncSessionLocal() as session:
                job = await session.get(ResearchJob, job_id)
                if not job:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                    return

                step_log = job.step_log or []

                # Emit any new steps
                new_steps = step_log[last_step_count:]
                for step in new_steps:
                    yield f"data: {json.dumps(step)}\n\n"
                    last_step_count += 1

                if job.status == "complete":
                    yield f"data: {json.dumps({'type': 'complete', 'job_id': job_id})}\n\n"
                    return
                elif job.status == "failed":
                    yield f"data: {json.dumps({'type': 'error', 'message': job.error_message})}\n\n"
                    return

            await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Prospect Routes (backend/routers/prospects.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.orm import Prospect
from ..models.schemas import ProspectCreate, ProspectResponse

router = APIRouter(prefix="/api/prospects", tags=["prospects"])

@router.post("/", response_model=ProspectResponse)
async def create_prospect(body: ProspectCreate, db: AsyncSession = Depends(get_db)):
    prospect = Prospect(
        company_name=body.company_name,
        website_url=body.website_url,
        status="queued"
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect

@router.get("/", response_model=list[ProspectResponse])
async def list_prospects(db: AsyncSession = Depends(get_db)):
    ...  # order by alignment_score desc, then created_at

@router.get("/{prospect_id}", response_model=ProspectResponse)
async def get_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    ...

@router.delete("/{prospect_id}")
async def delete_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    ...
```

### Letter Routes (backend/routers/letters.py)

```python
@router.post("/{prospect_id}/regenerate")
async def regenerate_letter(
    prospect_id: str,
    body: RegenerateRequest,  # { instructions: str }
    db: AsyncSession = Depends(get_db)
):
    """
    Rewrite the letter with specific instructions.
    Marks previous letter as not current, creates new version.
    """
    # Get existing dossier + matched content
    # Run writer agent with instructions appended to prompt
    # Save new letter as version N+1, mark previous is_current=False
    ...
```

### Chat Route (backend/routers/chat.py)

```python
@router.post("/stream")
async def chat_stream(body: ChatRequest):  # { session_id, message }
    """Streaming chat with the co-pilot agent."""
    async def generate():
        agent = create_chat_agent(settings.DATABASE_URL_SYNC)
        async for chunk in agent.astream(
            message=body.message,
            session_id=body.session_id,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 11. Frontend Architecture

### AgentProgressStream Component

```tsx
// components/AgentProgressStream.tsx
"use client";
import { useEffect, useState } from "react";
import { CheckCircle, Circle, Loader2, XCircle } from "lucide-react";

const STEPS = [
  { key: "qualifier", label: "Qualifying Prospect", description: "Scoring mission alignment" },
  { key: "researcher", label: "Deep Research", description: "Scraping ESG reports & leadership" },
  { key: "narrative_matcher", label: "Matching Stories", description: "Finding your best programs & stories" },
  { key: "writer", label: "Writing Materials", description: "Drafting briefing doc & letter" },
];

type StepStatus = "pending" | "running" | "complete" | "error";

export function AgentProgressStream({ jobId, onComplete }: {
  jobId: string;
  onComplete: () => void;
}) {
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>({});
  const [currentMessage, setCurrentMessage] = useState("");

  useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`/api/research/stream/${jobId}`);

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "complete") {
        setStepStatuses(prev => ({ ...prev, writer: "complete" }));
        es.close();
        onComplete();
        return;
      }
      if (data.type === "error") {
        setStepStatuses(prev => ({ ...prev, [data.step]: "error" }));
        es.close();
        return;
      }

      // Update step status
      if (data.step && data.status) {
        setStepStatuses(prev => ({ ...prev, [data.step]: data.status }));
      }
      if (data.message) {
        setCurrentMessage(data.message);
      }
    };

    return () => es.close();
  }, [jobId]);

  return (
    <div className="space-y-4 p-6 bg-white rounded-xl border">
      <h3 className="font-semibold text-gray-900">Research in Progress</h3>
      {STEPS.map((step) => {
        const status = stepStatuses[step.key] || "pending";
        return (
          <div key={step.key} className="flex items-start gap-3">
            <div className="mt-0.5">
              {status === "complete" && <CheckCircle className="w-5 h-5 text-green-500" />}
              {status === "running" && <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />}
              {status === "error" && <XCircle className="w-5 h-5 text-red-500" />}
              {status === "pending" && <Circle className="w-5 h-5 text-gray-300" />}
            </div>
            <div>
              <p className={`font-medium text-sm ${status === "running" ? "text-blue-700" : status === "complete" ? "text-gray-700" : "text-gray-400"}`}>
                {step.label}
              </p>
              <p className="text-xs text-gray-500">{step.description}</p>
              {status === "running" && currentMessage && (
                <p className="text-xs text-blue-500 mt-1 animate-pulse">{currentMessage}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

---

### LetterEditor Component

```tsx
// components/LetterEditor.tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export function LetterEditor({ prospectId, letter, onRegenerate }: {
  prospectId: string;
  letter: { body: string; decision_maker_name: string; version: number };
  onRegenerate: (newLetter: any) => void;
}) {
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [showInstructionInput, setShowInstructionInput] = useState(false);

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      const result = await api.regenerateLetter(prospectId, instructions);
      onRegenerate(result);
      setInstructions("");
      setShowInstructionInput(false);
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Introduction Letter</h3>
          <p className="text-xs text-gray-500">To: {letter.decision_maker_name} · v{letter.version}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowInstructionInput(!showInstructionInput)}>
          Rewrite with Instructions
        </Button>
      </div>

      {showInstructionInput && (
        <div className="space-y-2 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm font-medium text-blue-900">What should change?</p>
          <Textarea
            placeholder='e.g. "Lead with volunteering angle" or "Make it more casual" or "Contact went to Columbia, mention neighborhood connection"'
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={2}
          />
          <Button size="sm" onClick={handleRegenerate} disabled={isRegenerating || !instructions}>
            {isRegenerating ? "Rewriting..." : "Rewrite Letter"}
          </Button>
        </div>
      )}

      {/* Letter display */}
      <div className="p-6 bg-gray-50 rounded-lg border font-serif text-sm leading-relaxed whitespace-pre-wrap">
        {letter.body}
      </div>

      <Button variant="outline" size="sm" onClick={() => {
        navigator.clipboard.writeText(letter.body);
      }}>
        Copy to Clipboard
      </Button>
    </div>
  );
}
```

---

### API Client (frontend/lib/api.ts)

```typescript
import axios from "axios";

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
});

export const api = {
  // Prospects
  createProspect: (data: { company_name: string; website_url: string }) =>
    client.post("/api/prospects/", data).then(r => r.data),

  listProspects: () =>
    client.get("/api/prospects/").then(r => r.data),

  getProspect: (id: string) =>
    client.get(`/api/prospects/${id}`).then(r => r.data),

  // Research
  runResearch: (prospectId: string) =>
    client.post(`/api/research/${prospectId}/run`).then(r => r.data),

  // Letters
  getLetter: (prospectId: string) =>
    client.get(`/api/letters/${prospectId}`).then(r => r.data),

  regenerateLetter: (prospectId: string, instructions: string) =>
    client.post(`/api/letters/${prospectId}/regenerate`, { instructions }).then(r => r.data),

  // Chat
  streamChat: (sessionId: string, message: string) => {
    return new EventSource(
      `/api/chat/stream?session_id=${sessionId}&message=${encodeURIComponent(message)}`
    );
  },
};
```

---

## 12. Docker Setup

### docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: harlem_grown_db
    environment:
      POSTGRES_DB: harlem_grown
      POSTGRES_USER: hg_user
      POSTGRES_PASSWORD: hg_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hg_user -d harlem_grown"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
    driver: local
```

### backend/sql/init.sql

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

---

## 13. Build Order for Claude Code

Follow this sequence exactly. Each phase should be complete and tested before moving to the next.

```
PHASE 1 — INFRASTRUCTURE
─────────────────────────────────────────────────────
[ ] 1.  docker-compose.yml + backend/sql/init.sql
[ ] 2.  .env file (with placeholder values)
[ ] 3.  backend/config.py (Pydantic Settings class)
[ ] 4.  backend/database.py (async engine, session factory, get_db dep)
[ ] 5.  backend/models/orm.py (all SQLAlchemy models)
[ ] 6.  backend/models/schemas.py (all Pydantic schemas)
[ ] 7.  Alembic init + alembic/env.py (async config)
[ ] 8.  alembic/versions/001_initial_schema.py (all tables)
[ ] 9.  Run: docker compose up -d
[ ] 10. Run: alembic upgrade head
        VERIFY: all tables exist in postgres

PHASE 2 — TOOLS
─────────────────────────────────────────────────────
[ ] 11. backend/tools/scraper.py (crawl4ai wrappers)
[ ] 12. backend/tools/pdf_extractor.py (pymupdf)
[ ] 13. backend/tools/db_tools.py (agent-callable DB queries)
        VERIFY: scrape_page("https://example.com") returns markdown

PHASE 3 — RAG LAYER
─────────────────────────────────────────────────────
[ ] 14. knowledge_base/ — all 4 markdown files (stub content)
[ ] 15. backend/rag/loader.py (chunk + embed → pgvector)
[ ] 16. backend/rag/retriever.py (cosine similarity search)
        VERIFY: load KB, then query "youth education programs" returns results

PHASE 4 — AGENTS
─────────────────────────────────────────────────────
[ ] 17. Pydantic response models for each agent
        (QualificationResult, ResearchResult, NarrativeMatchResult, WriterOutput)
[ ] 18. backend/agents/qualifier.py
[ ] 19. backend/agents/researcher.py
[ ] 20. backend/agents/narrative_matcher.py
[ ] 21. backend/agents/writer.py
[ ] 22. backend/agents/team.py (Agno Team, sequential mode)
[ ] 23. backend/agents/chat_agent.py
        VERIFY: Run qualifier agent standalone on a test company URL

PHASE 5 — API LAYER
─────────────────────────────────────────────────────
[ ] 24. backend/routers/prospects.py (CRUD)
[ ] 25. backend/routers/research.py (trigger + SSE stream)
[ ] 26. backend/routers/letters.py (get + regenerate)
[ ] 27. backend/routers/chat.py (streaming chat)
[ ] 28. backend/main.py (assemble app, CORS, startup events)
        VERIFY: uvicorn main:app starts, /docs loads

PHASE 6 — FRONTEND
─────────────────────────────────────────────────────
[ ] 29. Next.js scaffold (create-next-app + shadcn init)
[ ] 30. frontend/lib/types.ts (TypeScript interfaces)
[ ] 31. frontend/lib/api.ts (typed API client)
[ ] 32. frontend/components/Navbar.tsx
[ ] 33. frontend/components/AlignmentScoreBar.tsx
[ ] 34. frontend/components/ProspectTable.tsx
[ ] 35. frontend/app/page.tsx (dashboard — stats + table)
[ ] 36. frontend/components/AgentProgressStream.tsx (SSE visualization)
[ ] 37. frontend/app/research/page.tsx (add prospect form)
[ ] 38. frontend/components/DossierCard.tsx
[ ] 39. frontend/components/LetterEditor.tsx
[ ] 40. frontend/app/prospects/[id]/page.tsx (dossier + letter view)
[ ] 41. frontend/components/ChatInterface.tsx
[ ] 42. frontend/app/chat/page.tsx
        VERIFY: Full flow — add prospect → research → view letter → chat

PHASE 7 — SEED DATA
─────────────────────────────────────────────────────
[ ] 43. seed/seed_demo_data.py
        VERIFY: Script runs, 4 demo prospects visible in dashboard
```

---

## 14. Demo Seed Data

### seed/seed_demo_data.py

Pre-load these four companies with realistic dossiers and letters so the demo doesn't require waiting for live scraping.

```python
"""
Run with: python seed/seed_demo_data.py
Pre-loads 4 demo prospects so the demo is immediately impressive.
"""

DEMO_PROSPECTS = [
    {
        "company_name": "Goldman Sachs",
        "website_url": "https://www.goldmansachs.com",
        "status": "complete",
        "alignment_score": 47.0,
        "go_no_go": True,
        "alignment_breakdown": {
            "youth_development": 9,
            "food_nutrition": 5,
            "environmental_sustainability": 8,
            "nyc_harlem_focus": 9,
            "workforce_development": 9,
            "employee_engagement": 7
        },
        "dossier": {
            "company_summary": (
                "Goldman Sachs is a global investment bank headquartered in New York City "
                "with a deeply rooted commitment to community development through the Goldman Sachs "
                "Foundation and its 10,000 Small Businesses and 10,000 Women programs. Their community "
                "investment strategy emphasizes economic mobility, workforce development, and support for "
                "underserved New York City neighborhoods, including a long history of engagement in Harlem."
            ),
            "esg_priorities": [
                {"priority": "Economic Mobility & Workforce Development",
                 "evidence": "We believe economic growth is most powerful when it is broadly shared — supporting small businesses and job training in underserved communities.",
                 "importance": "high"},
                {"priority": "NYC Community Investment",
                 "evidence": "Our community engagement is deeply rooted in New York, where we have operated for over 150 years and where we are committed to supporting the communities where our people live and work.",
                 "importance": "high"},
                {"priority": "Environmental Sustainability",
                 "evidence": "Goldman Sachs has committed $750 billion in sustainable finance by 2030, including investments in clean energy and sustainable food systems.",
                 "importance": "medium"},
            ],
            "csuite_contacts": [
                {"name": "Margaret Anadu",
                 "title": "Global Head of Sustainability and Impact, Asset Management",
                 "bio_snippet": "Former head of Urban Investment Group, deep Harlem community ties, Yale Law",
                 "is_primary_contact": True,
                 "contact_rationale": "Leads all community investment and impact initiatives; prior role was specifically NYC urban community investment"}
            ],
            "giving_patterns": {
                "typical_range": "$50K-$500K",
                "preferred_engagement_types": ["program_sponsorship", "workforce_development", "employee_volunteer_days"],
                "past_nonprofit_partners": ["Harlem Children's Zone", "Robin Hood Foundation", "City Harvest"],
                "decision_timeline": "Q3-Q4 budget planning",
                "value_language": "economic mobility, broadly shared growth, underserved communities, workforce readiness"
            }
        },
        "letter": {
            "decision_maker_name": "Margaret Anadu",
            "decision_maker_title": "Global Head of Sustainability and Impact",
            "letter_body": """Dear Margaret,

Your work building the Urban Investment Group into one of Wall Street's most impactful community investment vehicles — and your specific focus on Harlem — is exactly why I'm reaching out.

Harlem Grown operates 14 urban farms between 122nd and 152nd Streets, providing free programming to 18,000 youth annually through hands-on education in urban farming, nutrition, and sustainability. But our work is really about what you've spent your career championing: economic mobility, starting young. The children who learn to grow food on our farms go home and change how their families eat. The young adults in our workforce development program enter the job market with certifications, confidence, and a community behind them.

Our impact language maps directly to Goldman's: broadly shared growth, underserved New York communities, workforce readiness. The difference is we're doing it one child at a time, twelve inches of Harlem soil at a time.

I'd love to invite you and a few colleagues for a 90-minute visit to our flagship farm on 128th Street. Our students will give the tour. I think you'll understand immediately why 70% of our corporate visitors become partners.

Would you have 90 minutes in the next few weeks?

Warm regards,
[Name]
Development Team, Harlem Grown""",
            "briefing_doc": "# Goldman Sachs — Staff Briefing\n\n## Company at a Glance\n..."
        }
    },
    {
        "company_name": "Whole Foods Market",
        "website_url": "https://www.wholefoodsmarket.com",
        "status": "complete",
        "alignment_score": 52.0,
        # ... similar structure
    },
    {
        "company_name": "Northwell Health",
        "website_url": "https://www.northwell.edu",
        "status": "complete",
        "alignment_score": 49.0,
        # ... (note: already a real Harlem Grown partner — show in demo
        # as "EXISTING PARTNER — Do Not Contact" to show system intelligence)
    },
    {
        "company_name": "Salesforce",
        "website_url": "https://www.salesforce.com",
        "status": "complete",
        "alignment_score": 41.0,
        # ... tech company, different tone in letter
    },
]

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_all())
```

---

## 15. Code Examples — Critical Patterns

### FastAPI App Entry Point (backend/main.py)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models.orm import Base
from .rag.loader import load_knowledge_base
from .routers import prospects, research, letters, chat
from .config import settings
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize KB if empty. Shutdown: cleanup."""
    logger.info("Starting Harlem Grown Prospect Intelligence System")
    async with AsyncSessionLocal() as session:
        chunk_count = await session.scalar(select(func.count(KnowledgeChunk.id)))
        if chunk_count == 0:
            logger.info("Loading knowledge base into pgvector...")
            await load_knowledge_base(session)
        else:
            logger.info(f"Knowledge base ready: {chunk_count} chunks loaded")
    yield
    logger.info("Shutting down")

app = FastAPI(
    title="Harlem Grown Prospect Intelligence",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prospects.router)
app.include_router(research.router)
app.include_router(letters.router)
app.include_router(chat.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "harlem-grown-prospect-intelligence"}
```

### Agno Agent Step Logging Pattern

Each agent must log its progress to the ResearchJob step_log so the SSE stream has events to emit:

```python
async def log_step(job_id: str, step: str, status: str, message: str):
    """Call this at start and end of each agent step."""
    import datetime
    event = {
        "step": step,
        "status": status,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    async with AsyncSessionLocal() as session:
        job = await session.get(ResearchJob, job_id)
        if job:
            log = job.step_log or []
            log.append(event)
            job.step_log = log
            job.current_step = step
            await session.commit()
```

### Running the System (startup commands)

```bash
# Terminal 1 — Start database
docker compose up -d
# Wait for healthy status
docker compose ps

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
crawl4ai-setup          # one-time Playwright install
alembic upgrade head    # run migrations
uvicorn main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev             # runs on port 3000

# Terminal 4 — Seed demo data
python seed/seed_demo_data.py

# Open: http://localhost:3000
```

---

*PRD Version 1.0 — Harlem Grown Hackathon Build*
*Stack: Python + FastAPI + Agno + PostgreSQL/pgvector + Crawl4AI + Next.js*
