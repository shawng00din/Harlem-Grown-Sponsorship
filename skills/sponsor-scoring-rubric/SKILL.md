---
name: sponsor-scoring-rubric
description: 10-dimension scoring framework for Harlem Grown corporate sponsor qualification. Covers dimension rubrics (0-10 each), tier thresholds (PRIORITY/STRONG/POSSIBLE/MONITOR/PASS), archetype profiles (A-F), and confidence flags. Load this skill whenever scoring a company or assigning a tier.
metadata:
  version: "1.0.0"
  author: harlem-grown
  tags: ["qualification", "scoring", "sponsorship", "nonprofit"]
---

# Sponsor Scoring Rubric Skill

Load this skill when you are about to score a company against Harlem Grown's
10-dimension framework, assign a tier, or identify a company archetype.

## When to Use

- User asks you to qualify or score a company
- You have scraped CSR data and are ready to assign dimension scores
- You need to determine if a company is PRIORITY, STRONG, POSSIBLE, MONITOR, or PASS
- You need to assign an archetype (A–F) and identify the lead outreach angle
- You need to explain why a score was assigned or justify a tier decision

## When NOT to Load

- User is asking about existing reports or file management
- User is asking a general question about Harlem Grown
- You are only scraping — not yet scoring

## How to Use This Skill

1. Call `get_skill_instructions("sponsor-scoring-rubric")` to load this full guidance
2. Call `get_skill_reference("sponsor-scoring-rubric", "references/scoring-rubric.md")`
   to load the complete 10-dimension rubric tables and tier thresholds
3. Call `get_skill_reference("sponsor-scoring-rubric", "references/archetypes.md")`
   to load the 6 archetype profiles and lead angles

## Scoring Process

1. Load `references/scoring-rubric.md` — score each dimension 0–10 based on evidence found
2. Sum all 10 dimensions for the total (0–100)
3. Map total to tier using the threshold table in the rubric reference
4. Load `references/archetypes.md` — identify the best-fit archetype
5. Set confidence flag (HIGH/MEDIUM/LOW) based on CSR data quality
6. Save the qualification report before responding

## Critical Rules

- Dim 5 (Employee Volunteer Engagement) is the MOST PREDICTIVE dimension — weight evidence here carefully
- Dims 1, 2, 3, 7 all depend on CSR page quality — if the page was thin or missing, set confidence=LOW
- Only PRIORITY (80–100) and STRONG (60–79) companies go to the Researcher Agent
- Never assign PRIORITY or STRONG based on company size alone — evidence is required
