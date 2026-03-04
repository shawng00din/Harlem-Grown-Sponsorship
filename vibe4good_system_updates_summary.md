# Vibe4Good / Harlem Grown — System Summary for CLAUDE.md Update

### What We're Building
A multi-agent prospect intelligence system that helps Harlem Grown (NYC urban farm nonprofit) identify and prioritize corporate sponsors. The system finds companies likely to fund HG based on ESG alignment, NYC presence, sector fit, and giving history.

---

## Architecture: Three Agents

### Agent 1 — Discovery Agent
Generates the raw candidate list using structured filters. No scoring, no scraping. Fast and cheap.

**Filters:**
- Geography: NYC metro (Manhattan, Brooklyn, Queens, Bronx, Newark, Jersey City)
- Industry: Food/CPG, Healthcare, Financial Services, Insurance, Retail, Tech, Real Estate, Media
- Size floor: $50M+ revenue OR 200+ employees (proxy for formal CSR budget)
- Exclusion: Known HG partners (hardcoded list)

**Primary data source:** The Companies API (free tier, 500 credits, queryable by location + industry + employee count)  
**Fallback:** Curated seed list of ~100 NYC companies across target sectors

**Output:** Raw candidate list of 200–500 companies with name, domain, industry, size, HQ city

---

### Agent 2 — Qualifier Agent
For each candidate from Agent 1, finds and parses their ESG/CSR presence and scores them on 10 dimensions (0–10 each, total 0–100). Threshold for outreach: 60/100.

**CSR Detection Logic:**
1. Web search: `"{company}" CSR OR ESG OR "corporate responsibility" site:{domain}`
2. Check common CSR URL patterns: `/sustainability`, `/responsibility`, `/csr`, `/esg`, `/community`, `/impact`
3. If found: Crawl with Crawl4AI, extract text, pass to Claude with scorecard rubric
4. If not found: Score dimensions 1, 2, 3, 7 at 2–3, flag "Limited ESG presence"

**10 Scoring Dimensions + Data Sources:**

| # | Dimension | Source | Method |
|---|---|---|---|
| 1 | Food & Nutrition Alignment | Crawl4AI → Claude | Infer from CSR page text |
| 2 | Youth & Education Alignment | Crawl4AI → Claude | Infer from CSR page text |
| 3 | Environmental Sustainability | B Corp/1% for Planet + CSR scrape | Pre-qualified lists + inference |
| 4 | NYC/Harlem Proximity | The Companies API | Direct field (HQ city) |
| 5 | Employee Volunteer Appetite | Double the Donation API | Direct — VTO/volunteer grant programs |
| 6 | Giving Capacity | Companies API revenue/headcount | Proxy — not actual giving dollars |
| 7 | ESG Values Language Match | Crawl4AI → Claude | Claude reads and scores language quality |
| 8 | Decision-Maker Accessibility | Web search | Weakest dimension — 50% coverage |
| 9 | Sector Narrative Fit | Companies API industry → rules | Deterministic rules mapping |
| 10 | Partnership Longevity Potential | Double the Donation history | Inferred from program age/history |

**Confidence flag:** If CSR page is rich → HIGH confidence. Thin page → MEDIUM. No page → LOW. Surface this in output.

**Output per company:**
- Total score (0–100) and tier (PRIORITY / STRONG / POSSIBLE / MONITOR / PASS)
- Archetype match (A–F from framework)
- Top 3 signals found
- Strongest pitch angle
- Biggest gap
- Recommended HG program to lead with
- Decision-maker hypothesis
- Existing partner flag

---

### Agent 3 — Researcher Agent
Deep research on PRIORITY and STRONG tier companies only. Produces the outreach brief.

**Inputs:** Qualifier output for a single company  
**Tasks:**
- Find named CSR/foundation contacts (title: CSR Director, VP Community Affairs, Head of Philanthropy)
- Pull recent grants or partnerships from news/press releases
- Identify any Harlem or upper Manhattan connection
- Draft a tailored pitch hook based on archetype

**Output:** One-page outreach brief per company ready for human review

---

## Data Pipeline Summary

**Pipeline A — Structured firmographics:** The Companies API → dimensions 4, 6, 9

**Pipeline B — Unstructured CSR content:** Crawl4AI + Claude → dimensions 1, 2, 3, 7 (all from same CSR page crawl — known single point of failure, flagged via confidence score)

**Pipeline C — Volunteer/giving programs:** Double the Donation API → dimensions 5, partial 10

**Pipeline D — Decision-maker discovery:** Web search → dimension 8 (weakest, manual fallback acceptable)

---

## Tech Stack
- **Agent OS:** Agno
- **Web scraping:** Crawl4AI
- **Database:** PostgreSQL with pgvector
- **Firmographic data:** The Companies API (free tier)
- **Volunteer/giving data:** Double the Donation API
- **ESG pre-qualification lists:** B Corp directory scrape, 1% for the Planet directory scrape
- **LLM inference:** Claude (scoring, pitch generation, researcher output)

---

## Known Limitations to Document
1. Pipeline B (4 dimensions) relies on a single CSR page — thin pages degrade 40% of the score simultaneously
2. Dimension 8 (decision-maker) has only ~50% automated coverage
3. Giving capacity (dimension 6) is a proxy from revenue/headcount, not actual philanthropic spend
4. The Companies API free tier is 500 credits — sufficient for demo, needs paid plan for production scale
5. Double the Donation is nonprofit-priced but still requires API access approval
