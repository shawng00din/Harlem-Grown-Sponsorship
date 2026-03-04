"""
Harlem Grown Prospect Intelligence — AgentOS

Run:
    uv run python main.py

Then connect at https://os.agno.com → Add new OS → http://localhost:7777

WHAT'S AVAILABLE IN THE UI:

  Teams:
    Prospect Intelligence Team — full end-to-end pipeline in one conversation.
    The team leader coordinates Discovery → Qualifier → Researcher automatically.
    Use this for most tasks.

  Individual Agents (for focused single-step work):
    Discovery Agent  — find candidate companies
    Qualifier Agent  — score a specific company
    Researcher Agent — write the outreach brief + letter

MEMORY, LEARNING & TRACING:
  All agents and the team share hg_memory.db (SQLite).
  Conversations, user preferences, and learned patterns persist across sessions.
  learning=True means agents automatically capture what works and improve over time.
  Tracing via OpenTelemetry → DatabaseSpanExporter → visible in AgentOS UI traces tab.
"""
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import anthropic
import logging
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from agno.tracing import setup_tracing

from agents.discovery import create_discovery_agent
from agents.qualifier import create_qualifier_agent
from agents.researcher import create_researcher_agent
from agents.team import create_prospect_team

logger = logging.getLogger(__name__)

for _d in ["outputs/discovery", "outputs/qualified", "outputs/research", "outputs/pdfs"]:
    Path(_d).mkdir(parents=True, exist_ok=True)

# Shared SQLite db — memory, sessions, and traces all in one file
db = SqliteDb(db_file="hg_memory.db")

# Enable OpenTelemetry tracing → stored in hg_memory.db → visible in AgentOS UI
setup_tracing(db=db)
logger.info("✓ Agno tracing enabled → hg_memory.db")

# Validate Anthropic key on startup
try:
    anthropic.Anthropic().models.list()
    logger.info("✓ Anthropic API key valid")
except anthropic.AuthenticationError:
    logger.error("✗ ANTHROPIC_API_KEY is invalid — check your .env file")
except anthropic.PermissionDeniedError as e:
    logger.warning(f"✗ Anthropic billing issue: {e} — add credits at console.anthropic.com/settings/billing")
except Exception:
    pass

agent_os = AgentOS(
    name="Harlem Grown Prospect Intelligence",
    teams=[create_prospect_team()],
    agents=[
        create_discovery_agent(),
        create_qualifier_agent(),
        create_researcher_agent(),
    ],
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve("main:app", reload=True)
