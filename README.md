# Harlem Grown Prospect Intelligence

An AI-powered multi-agent system that helps [Harlem Grown](https://harlemgrown.org) — a NYC nonprofit operating 14 urban farms in Central Harlem — identify, score, and craft personalized outreach to corporate sponsors.

---

## What It Does

Three specialist agents work together (or independently) to run a full corporate development pipeline:

| Agent | Model | Job |
|---|---|---|
| **Discovery Agent** | Claude Haiku 4.5 | Finds NYC companies via The Companies API and a curated seed list, filtered by sector and size |
| **Qualifier Agent** | Claude Haiku 4.5 | Scores each company on 10 dimensions (0–100), assigns a tier and archetype |
| **Researcher Agent** | Claude Sonnet 4.5 | Deep-dives PRIORITY and STRONG companies — produces a staff outreach brief, personalized introduction letter, and 3-step follow-up path |

The **Prospect Intelligence Team** coordinates all three automatically when given an end-to-end request.

---

## Scoring System

Each company receives a 0–10 score on 10 dimensions (100 total):

1. Food & Nutrition Alignment
2. Youth & Education Alignment
3. Environmental Sustainability
4. NYC / Harlem Community Proximity
5. Employee Volunteer Appetite ← *most predictive dimension*
6. Giving Capacity
7. ESG Values Language Match
8. Decision-Maker Accessibility
9. Sector Narrative Fit
10. Partnership Longevity Potential

**Tiers:** `PRIORITY` (80–100) · `STRONG` (60–79) · `POSSIBLE` (40–59) · `MONITOR` (25–39) · `PASS` (<25)

**Archetypes:** A (Mission Soulmate) · B (Community Health Champion) · C (Resilient Financier) · D (Purpose-Driven Consumer Brand) · E (Tech Neighbor) · F (Real Estate Transformer)

Only PRIORITY and STRONG companies proceed to full research and letter writing.

---

## Stack

- **Agents:** [Agno](https://docs.agno.com) — coordinate-mode team with persistent memory and learning
- **LLMs:** Anthropic Claude (Haiku 4.5 for discovery/qualification, Sonnet 4.5 for research)
- **Memory:** SQLite via Agno (`hg_memory.db`) — agents remember context across sessions
- **File I/O:** Agno `FileTools` — agents save markdown reports and read each other's outputs
- **Scraping:** Crawl4AI — async web crawler for CSR/ESG pages
- **Data:** The Companies API + curated NYC seed list fallback
- **UI:** [os.agno.com](https://os.agno.com) — hosted AgentOS interface, connect to local server

---

## Project Structure

```
harlem-grown/
├── main.py                    # AgentOS entry point — registers agents + team
├── config.py                  # Pydantic Settings — all env vars
├── agents/
│   ├── discovery.py           # Discovery Agent
│   ├── qualifier.py           # Qualifier Agent (10-dim scoring)
│   ├── researcher.py          # Researcher Agent (brief + letter)
│   └── team.py                # Prospect Intelligence Team
├── tools/
│   ├── scraper.py             # Crawl4AI wrappers
│   ├── companies_api.py       # The Companies API + seed list fallback
│   └── kb_tools.py            # Knowledge base read functions
├── models/
│   └── schemas.py             # Pydantic output models (DiscoveryResult, QualificationResult, ResearchResult)
├── knowledge_base/
│   ├── harlem_grown_overview.md
│   ├── programs.md
│   ├── impact_stories.md
│   ├── sponsorship_tiers.md
│   └── sponsor_criteria_framework.md   # The scoring bible — 10 dims + archetypes
├── seed/
│   └── curated_seed_list.json  # ~100 NYC companies fallback
├── test_agents.py              # Programmatic test runner via AgentOS REST API
└── .env.example                # Environment variable template
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/shawng00din/Harlem-Grown-Sponsorship.git
cd Harlem-Grown-Sponsorship

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# One-time: install Crawl4AI browser dependencies
uv run crawl4ai-setup
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Required:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

Optional (agents fall back gracefully without these):
```env
COMPANIES_API_KEY=...       # The Companies API — free tier, 500 credits
```

### 3. Start AgentOS

```bash
uv run python main.py
```

The server starts at `http://localhost:7777`. Open [os.agno.com](https://os.agno.com) and connect to `http://localhost:7777` to chat with agents in the hosted UI.

---

## Using the Agents

### Via the AgentOS UI (os.agno.com)

Connect to `http://localhost:7777` and chat with any agent individually or with the full team.

**Example prompts:**

| Agent | Prompt |
|---|---|
| Discovery | *"Find 20 NYC healthcare companies with 500+ employees that could be Harlem Grown sponsors"* |
| Qualifier | *"Qualify Goldman Sachs (goldmansachs.com) as a potential sponsor"* |
| Researcher | *"Research Whole Foods Market for Harlem Grown outreach — they scored STRONG (56/100), Archetype A"* |
| Team | *"Find a food and beverage company in NYC, qualify them, and if they're PRIORITY or STRONG write me an outreach letter"* |

### Via the REST API

The AgentOS server exposes a REST API at `http://localhost:7777/docs`.

```bash
# Qualify a company
curl -X POST http://localhost:7777/agents/qualifier/runs \
  -F "message=Qualify Whole Foods Market (wholefoodsmarket.com)" \
  -F "stream=false"

# Run the full team
curl -X POST http://localhost:7777/teams/prospect-team/runs \
  -F "message=Find and qualify 3 NYC financial services companies" \
  -F "stream=false"
```

### Programmatic test runner

```bash
# Run default tests (discovery + qualifier + partner guard)
uv run python test_agents.py

# Run specific tests
uv run python test_agents.py qualifier
uv run python test_agents.py team
uv run python test_agents.py pipeline   # full end-to-end (slow)
```

---

## Agent Outputs

Agents save reports to `outputs/` (gitignored — stays local):

```
outputs/
├── discovery/    # YYYY-MM-DD_discovery.md
├── qualified/    # {company}_qualified.md
└── research/     # {company}_research.md
```

Each research report includes:
- Staff briefing (company snapshot, why they match, who to contact, what angle to lead with)
- Personalized introduction letter (≤350 words, archetype-matched tone)
- 3-step follow-up path with email templates

---

## Agent Memory & Learning

All agents use Agno's built-in learning machine (`learning=True`) backed by SQLite. They:
- Remember companies scored in previous sessions
- Build a user profile over time (preferences, priorities, feedback)
- Accumulate institutional knowledge about what works for HG outreach

Memory is stored in `hg_memory.db` (local, gitignored).

---

## Known Partners (Never Cold Outreach)

FM Global · Northwell Health · Newman's Own Foundation · Wells Fargo Foundation · Warburg Pincus · Hairstory · Mellon Foundation

All agents are hardcoded to flag and exclude these from outreach recommendations.

---

## Development

The scoring rubric, tier thresholds, and all 6 archetype profiles live in `knowledge_base/sponsor_criteria_framework.md`. Edit this file to tune the qualification logic — agents read it at runtime.

To update the knowledge base without restarting:
- Edit any file in `knowledge_base/`
- The agents pick up changes on their next run (they read files via `read_knowledge_file()`)
