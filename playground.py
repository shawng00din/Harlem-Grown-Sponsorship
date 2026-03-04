"""
Harlem Grown Prospect Intelligence — AgentOS

HOW TO RUN:
    fastapi dev playground.py          # dev mode with hot reload (port 8000)
    fastapi run playground.py          # production mode

THEN CONNECT:
    1. Go to https://os.agno.com and sign in (free account)
    2. Click "Add new OS"
    3. Set Endpoint URL: http://localhost:8000
    4. Click CONNECT
    5. Your three agents appear in the chat interface — select each independently

THREE AGENTS:

  Discovery Agent
    Finds candidate companies via The Companies API (or seed list fallback).
    Example: "Find NYC food and healthcare companies with 500+ employees"
    Output: outputs/discovery/YYYY-MM-DD_discovery.md

  Qualifier Agent
    Scores companies on 10 dimensions (0–100), assigns tier + archetype (A–F).
    Example: "Qualify Sweetgreen at sweetgreen.com"
    Example: "Read the latest discovery report and qualify the top 5 companies"
    Output: outputs/qualified/{company}_qualified.md

  Researcher Agent
    Deep-dives PRIORITY and STRONG tier companies → outreach brief + letter.
    Example: "Research Sweetgreen — read their qualifier file first"
    Example: "Rewrite the Goldman Sachs letter to lead with the volunteer day angle"
    Output: outputs/research/{company}_research.md

FILE-BASED HANDOFF:
    Agents pass work to each other via ./outputs/
    Each agent has tools to list and read outputs from upstream agents.
    You can also paste a qualifier report directly into the Researcher chat.
"""
from pathlib import Path

from agno.os import AgentOS

from agents.discovery import create_discovery_agent
from agents.qualifier import create_qualifier_agent
from agents.researcher import create_researcher_agent


def ensure_output_dirs():
    for d in ["outputs/discovery", "outputs/qualified", "outputs/research", "outputs/pdfs"]:
        Path(d).mkdir(parents=True, exist_ok=True)


ensure_output_dirs()

agent_os = AgentOS(
    name="Harlem Grown Prospect Intelligence",
    agents=[
        create_discovery_agent(),
        create_qualifier_agent(),
        create_researcher_agent(),
    ],
)

app = agent_os.get_app()
