"""
Pydantic models for structured agent outputs.

Flow:
  DiscoveryResult  → QualificationResult → ResearchResult
  (Discovery)        (Qualifier)            (Researcher)

The team leader receives these typed objects and passes exact fields
(tier, archetype, key_signals) to the next agent — no prose parsing needed.

Each agent also writes a human-readable markdown file alongside the JSON.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class CompanyCandidate(BaseModel):
    name: str
    domain: str
    industry: str
    employee_count: Optional[int] = None
    city: str = "New York"
    notes: Optional[str] = None


class DiscoveryResult(BaseModel):
    search_filters: str = Field(description="Plain-language description of filters used")
    source: str = Field(description="'Companies API', 'Seed List', or 'Mixed'")
    candidates: list[CompanyCandidate]
    excluded_partners: list[str] = Field(
        default_factory=list,
        description="Known HG partners that appeared and were excluded"
    )
    notes: Optional[str] = None

    @computed_field
    @property
    def total_found(self) -> int:
        return len(self.candidates)

    def to_markdown(self) -> str:
        from datetime import date
        lines = [
            f"# Discovery Report — {date.today()}",
            f"**Filters:** {self.search_filters}",
            f"**Source:** {self.source}",
            f"**Total Candidates:** {self.total_found}",
            "",
            "---",
            "",
            "## Candidate List",
            "",
            "| # | Company | Domain | Industry | Est. Employees | City | Notes |",
            "|---|---------|--------|----------|----------------|------|-------|",
        ]
        for i, c in enumerate(self.candidates, 1):
            emp = str(c.employee_count) if c.employee_count else "—"
            notes = c.notes or ""
            lines.append(f"| {i} | {c.name} | {c.domain} | {c.industry} | {emp} | {c.city} | {notes} |")

        if self.excluded_partners:
            lines += ["", "---", "", "## Already-Known Partners (Excluded)", ""]
            for p in self.excluded_partners:
                lines.append(f"- {p}")

        if self.notes:
            lines += ["", "---", "", "## Notes", "", self.notes]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Qualification
# ---------------------------------------------------------------------------

class DimensionScores(BaseModel):
    food_nutrition_alignment: int = Field(ge=0, le=10)
    youth_education_alignment: int = Field(ge=0, le=10)
    environmental_sustainability: int = Field(ge=0, le=10)
    nyc_harlem_proximity: int = Field(ge=0, le=10)
    employee_volunteer_appetite: int = Field(ge=0, le=10)
    giving_capacity: int = Field(ge=0, le=10)
    esg_values_language_match: int = Field(ge=0, le=10)
    decision_maker_accessibility: int = Field(ge=0, le=10)
    sector_narrative_fit: int = Field(ge=0, le=10)
    partnership_longevity_potential: int = Field(ge=0, le=10)

    @computed_field
    @property
    def total(self) -> int:
        return sum([
            self.food_nutrition_alignment,
            self.youth_education_alignment,
            self.environmental_sustainability,
            self.nyc_harlem_proximity,
            self.employee_volunteer_appetite,
            self.giving_capacity,
            self.esg_values_language_match,
            self.decision_maker_accessibility,
            self.sector_narrative_fit,
            self.partnership_longevity_potential,
        ])


class QualificationResult(BaseModel):
    company_name: str
    website_url: str
    scores: DimensionScores
    tier: str = Field(description="PRIORITY | STRONG | POSSIBLE | MONITOR | PASS")
    archetype: str = Field(description="A | B | C | D | E | F | None")
    archetype_name: str = Field(description="e.g. 'The Resilient Financier'")
    confidence: str = Field(description="HIGH | MEDIUM | LOW")
    go_no_go: bool = Field(description="True if total_score >= 60")
    existing_partner: bool = False
    key_signals: list[str] = Field(description="3-5 verbatim evidence quotes from their site")
    strongest_angle: str = Field(description="Single most compelling pitch hook")
    biggest_gap: str = Field(description="Weakest dimension and what's missing")
    recommended_program: str = Field(description="Which HG program to lead with")
    decision_maker_hypothesis: str = Field(description="Who probably owns this decision and why")
    recommended_first_ask: str = Field(description="site_visit | volunteer_day | program_sponsor")
    raw_research_notes: Optional[str] = None

    def to_markdown(self) -> str:
        from datetime import date
        s = self.scores
        total = s.total
        lines = [
            f"# Qualification Report — {self.company_name}",
            f"**Date:** {date.today()}",
            f"**Website:** {self.website_url}",
            f"**Tier:** {self.tier}",
            f"**Total Score:** {total}/100",
            f"**Archetype:** {self.archetype} — {self.archetype_name}",
            f"**Confidence:** {self.confidence}",
            f"**Go/No-Go:** {'GO' if self.go_no_go else 'NO-GO'}",
            f"**Existing Partner:** {'Yes — DO NOT COLD OUTREACH' if self.existing_partner else 'No'}",
            "",
            "---",
            "",
            "## Score Breakdown",
            "",
            "| Dimension | Score | /10 |",
            "|-----------|-------|-----|",
            f"| 1. Food & Nutrition Alignment | {s.food_nutrition_alignment} | ██{'░' * (10 - s.food_nutrition_alignment)} |",
            f"| 2. Youth & Education Alignment | {s.youth_education_alignment} | ██{'░' * (10 - s.youth_education_alignment)} |",
            f"| 3. Environmental Sustainability | {s.environmental_sustainability} | ██{'░' * (10 - s.environmental_sustainability)} |",
            f"| 4. NYC / Harlem Proximity | {s.nyc_harlem_proximity} | ██{'░' * (10 - s.nyc_harlem_proximity)} |",
            f"| 5. Employee Volunteer Appetite | {s.employee_volunteer_appetite} | ██{'░' * (10 - s.employee_volunteer_appetite)} |",
            f"| 6. Giving Capacity | {s.giving_capacity} | ██{'░' * (10 - s.giving_capacity)} |",
            f"| 7. ESG Values Language Match | {s.esg_values_language_match} | ██{'░' * (10 - s.esg_values_language_match)} |",
            f"| 8. Decision-Maker Accessibility | {s.decision_maker_accessibility} | ██{'░' * (10 - s.decision_maker_accessibility)} |",
            f"| 9. Sector Narrative Fit | {s.sector_narrative_fit} | ██{'░' * (10 - s.sector_narrative_fit)} |",
            f"| 10. Partnership Longevity Potential | {s.partnership_longevity_potential} | ██{'░' * (10 - s.partnership_longevity_potential)} |",
            f"| **TOTAL** | **{total}/100** | |",
            "",
            "---",
            "",
            "## Key Signals Found",
            "",
        ]
        for i, sig in enumerate(self.key_signals, 1):
            lines.append(f"{i}. {sig}")

        lines += [
            "",
            "## Strongest Pitch Angle",
            "",
            self.strongest_angle,
            "",
            "## Biggest Gap",
            "",
            self.biggest_gap,
            "",
            "## Recommended HG Program",
            "",
            self.recommended_program,
            "",
            "## Decision-Maker Hypothesis",
            "",
            self.decision_maker_hypothesis,
            "",
            "## Recommended First Ask",
            "",
            self.recommended_first_ask,
        ]

        if self.raw_research_notes:
            lines += ["", "---", "", "## Raw Research Notes", "", self.raw_research_notes]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

class ESGPriority(BaseModel):
    priority: str
    evidence: str = Field(description="Verbatim quote from their materials")
    importance: str = Field(description="high | medium | low")


class Contact(BaseModel):
    name: str
    title: str
    bio_snippet: Optional[str] = None
    is_primary: bool = False
    rationale: str = Field(description="Why this person owns the sponsorship decision")


class MatchedProgram(BaseModel):
    program_name: str
    relevance_reason: str
    suggested_angle: str


class MatchedStory(BaseModel):
    story_title: str
    tags: list[str]
    why_it_resonates: str


class FollowUpStep(BaseModel):
    step: int
    timing: str
    action: str
    template: Optional[str] = None


class ResearchResult(BaseModel):
    company_name: str
    tier: str
    archetype: str
    archetype_name: str
    # Core outputs
    letter_body: str = Field(description="Personalized introduction letter, max 350 words")
    outreach_brief: str = Field(description="Staff briefing in markdown format")
    # Supporting data
    esg_priorities: list[ESGPriority]
    contacts: list[Contact]
    matched_programs: list[MatchedProgram]
    matched_stories: list[MatchedStory]
    follow_up_path: list[FollowUpStep]
    recommended_tier_ask: str = Field(description="e.g. 'Gold Partner — $50,000'")
    recommended_first_ask: str

    def to_markdown(self) -> str:
        from datetime import date
        lines = [
            f"# Research Report — {self.company_name}",
            f"**Date:** {date.today()}",
            f"**Tier:** {self.tier}",
            f"**Archetype:** {self.archetype} — {self.archetype_name}",
            "",
            "---",
            "",
            "## Staff Briefing",
            "",
            self.outreach_brief,
            "",
            "---",
            "",
            "## ESG Priorities",
            "",
        ]
        for p in self.esg_priorities:
            lines += [f"**{p.priority}** ({p.importance})", f"> {p.evidence}", ""]

        if self.contacts:
            lines += ["---", "", "## Key Contacts", ""]
            for c in self.contacts:
                primary = " ⭐ PRIMARY" if c.is_primary else ""
                lines += [
                    f"**{c.name}**, {c.title}{primary}",
                    f"*Why they own this:* {c.rationale}",
                ]
                if c.bio_snippet:
                    lines.append(f"*Background:* {c.bio_snippet}")
                lines.append("")

        lines += ["---", "", "## Matched HG Programs", ""]
        for p in self.matched_programs:
            lines += [f"**{p.program_name}**", f"- Why it fits: {p.relevance_reason}", f"- Angle: {p.suggested_angle}", ""]

        lines += ["---", "", "## Matched Impact Stories", ""]
        for s in self.matched_stories:
            tags = " ".join(f"`{t}`" for t in s.tags)
            lines += [f"**{s.story_title}** {tags}", f"- {s.why_it_resonates}", ""]

        lines += [
            "---",
            "",
            "## Introduction Letter",
            "",
            f"*Recommended ask: {self.recommended_tier_ask}*",
            f"*First ask: {self.recommended_first_ask}*",
            "",
            "---",
            "",
            self.letter_body,
            "",
            "---",
            "",
            "## Follow-Up Path",
            "",
        ]
        for step in self.follow_up_path:
            lines += [f"**Step {step.step} — {step.timing}:** {step.action}"]
            if step.template:
                lines += ["", f"```", step.template, "```"]
            lines.append("")

        return "\n".join(lines)
