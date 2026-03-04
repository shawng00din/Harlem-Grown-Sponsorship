"""
Read-only access to the Harlem Grown knowledge base.

Unique function names avoid collision with FileTools' read_file/list_files.
"""
from pathlib import Path

from config import settings

_KB_FILES = {
    "programs.md": "HG programs — school partnerships, summer camp, workforce development, mobile kitchen",
    "impact_stories.md": "Impact stories — youth testimonials, outcomes, partnership results",
    "harlem_grown_overview.md": "HG overview — history, mission, farms, team",
    "sponsorship_tiers.md": "Sponsorship tiers — Platinum/Gold/Silver/Community pricing and benefits",
    "sponsor_criteria_framework.md": "Scoring rubric — 10 dimensions, tier thresholds, archetypes A-F",
}


def list_knowledge_files() -> list[str]:
    """
    List all Harlem Grown knowledge base files.
    Returns filenames with a short description of each file's content.
    Use this before read_knowledge_file() to find the right document.
    """
    return [f"{name} — {desc}" for name, desc in _KB_FILES.items()]


def read_knowledge_file(filename: str) -> str:
    """
    Read a Harlem Grown knowledge base document by filename.
    Available files: programs.md, impact_stories.md, harlem_grown_overview.md,
    sponsorship_tiers.md, sponsor_criteria_framework.md.
    Returns the full document text.
    """
    kb = settings.kb_path()
    path = kb / filename
    if not path.exists():
        available = ", ".join(_KB_FILES.keys())
        return f"[File not found: {filename}. Available: {available}]"
    return path.read_text(encoding="utf-8")
