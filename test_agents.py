"""
Programmatic test runner for Harlem Grown agents via the AgentOS REST API.

Usage:
  uv run python test_agents.py                        # run all tests
  uv run python test_agents.py qualifier              # test only qualifier
  uv run python test_agents.py team                   # test only the full team
  uv run python test_agents.py discovery qualifier    # run specific tests

Requires AgentOS to be running:
  uv run python main.py
"""
import json
import sys
import time
from datetime import datetime

import httpx

BASE_URL = "http://localhost:7777"
TIMEOUT = 120  # seconds — research takes a while


# ---------------------------------------------------------------------------
# Core API helpers
# ---------------------------------------------------------------------------

def run_agent(agent_id: str, message: str) -> dict:
    """POST /agents/{agent_id}/runs — uses multipart/form-data, stream=false."""
    resp = httpx.post(
        f"{BASE_URL}/agents/{agent_id}/runs",
        data={"message": message, "stream": "false"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def run_team(team_id: str, message: str) -> dict:
    """POST /teams/{team_id}/runs — uses multipart/form-data, stream=false."""
    resp = httpx.post(
        f"{BASE_URL}/teams/{team_id}/runs",
        data={"message": message, "stream": "false"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def extract_content(response: dict) -> str:
    """Pull readable text out of an AgentOS run response.

    The non-streaming response shape is:
      { "run_id": ..., "content": "...", "status": "success"|"ERROR", ... }
    """
    status = response.get("status", "")
    content = response.get("content", "")

    if isinstance(content, str) and content:
        if status == "ERROR":
            return f"[ERROR] {content}"
        return content

    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )

    # Fallback: dump the whole response compactly
    return json.dumps(response, indent=2)[:800]


def hr(title: str = "") -> None:
    print("\n" + "─" * 60)
    if title:
        print(f"  {title}")
        print("─" * 60)


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

def test_discovery():
    hr("TEST: Discovery Agent — seed list lookup")
    print("Asking Discovery Agent to find 5 NYC food & beverage candidates...")
    start = time.time()

    result = run_agent(
        "discovery",
        "Find 5 NYC-based food and beverage companies with 200+ employees "
        "that could be Harlem Grown sponsors. Use the seed list if the API isn't available.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:800]}")

    # Basic assertions
    assert content, "Discovery returned empty response"
    print(f"\n✓ Discovery Agent responded in {elapsed}s")
    return result


def test_qualifier():
    hr("TEST: Qualifier Agent — score a known company")
    print("Asking Qualifier Agent to score Whole Foods Market...")
    start = time.time()

    result = run_agent(
        "qualifier",
        "Qualify Whole Foods Market (wholefoodsmarket.com) as a Harlem Grown sponsor. "
        "Score all 10 dimensions and assign a tier and archetype.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:1000]}")

    # Check for key fields in structured output
    assert content, "Qualifier returned empty response"
    print(f"\n✓ Qualifier Agent responded in {elapsed}s")
    return result


def test_qualifier_existing_partner():
    hr("TEST: Qualifier Agent — existing partner guard")
    print("Asking Qualifier to score Northwell Health (known HG partner)...")
    start = time.time()

    result = run_agent(
        "qualifier",
        "Qualify Northwell Health (northwell.edu) as a Harlem Grown sponsor candidate.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:600]}")

    # Should flag as existing partner
    assert "partner" in content.lower() or "existing" in content.lower(), \
        "FAIL: Qualifier didn't flag Northwell as an existing partner"
    print(f"\n✓ Qualifier correctly flagged existing partner in {elapsed}s")
    return result


def test_team_qualify():
    hr("TEST: Team — single company qualification")
    print("Asking the Prospect Intelligence Team to qualify Goldman Sachs...")
    start = time.time()

    result = run_team(
        "prospect-team",
        "Please qualify Goldman Sachs (goldmansachs.com) as a potential Harlem Grown "
        "corporate sponsor. Give me the score, tier, archetype, and strongest pitch angle.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:1200]}")

    assert content, "Team returned empty response"
    print(f"\n✓ Team responded in {elapsed}s")
    return result


def test_team_pipeline():
    hr("TEST: Team — full pipeline (discover → qualify → research)")
    print("Asking the Team to run the full pipeline for a healthcare company...")
    print("(This may take 2-3 minutes)")
    start = time.time()

    result = run_team(
        "prospect-team",
        "Find one NYC-based healthcare company with strong community health programs "
        "from our seed list, qualify them, and if they score STRONG or above, "
        "produce an outreach brief and introduction letter.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:2000]}")

    assert content, "Team pipeline returned empty response"
    print(f"\n✓ Full pipeline completed in {elapsed}s")
    return result


def test_team_pass_guard():
    hr("TEST: Team — PASS tier gate")
    print("Asking Team to research a company that should score low...")
    start = time.time()

    result = run_team(
        "prospect-team",
        "Research and produce an outreach letter for Exxon Mobil.",
    )

    elapsed = round(time.time() - start, 1)
    content = extract_content(result)
    print(f"Response ({elapsed}s):\n{content[:600]}")

    # Team should refuse to run full research on a low-scoring company
    assert "pass" in content.lower() or "not recommend" in content.lower() \
        or "score" in content.lower(), \
        "WARN: Team may have run full research on a likely-PASS company"
    print(f"\n✓ Team handled low-tier company appropriately in {elapsed}s")
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = {
    "discovery": test_discovery,
    "qualifier": test_qualifier,
    "qualifier_partner": test_qualifier_existing_partner,
    "team": test_team_qualify,
    "pipeline": test_team_pipeline,
    "pass_guard": test_team_pass_guard,
}

DEFAULT_TESTS = ["discovery", "qualifier", "qualifier_partner", "team"]


def main():
    requested = sys.argv[1:] or DEFAULT_TESTS
    unknown = [t for t in requested if t not in TESTS]
    if unknown:
        print(f"Unknown tests: {unknown}")
        print(f"Available: {list(TESTS.keys())}")
        sys.exit(1)

    # Check server is up
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5).raise_for_status()
    except Exception:
        print(f"✗ AgentOS not running at {BASE_URL}")
        print("  Start it with: uv run python main.py")
        sys.exit(1)

    print(f"\n{'═' * 60}")
    print(f"  Harlem Grown Agent Tests — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Running: {', '.join(requested)}")
    print(f"{'═' * 60}")

    passed, failed = [], []

    for name in requested:
        try:
            TESTS[name]()
            passed.append(name)
        except AssertionError as e:
            print(f"\n✗ ASSERTION FAILED: {e}")
            failed.append(name)
        except httpx.HTTPStatusError as e:
            print(f"\n✗ HTTP ERROR {e.response.status_code}: {e.response.text[:300]}")
            failed.append(name)
        except Exception as e:
            print(f"\n✗ ERROR: {type(e).__name__}: {e}")
            failed.append(name)

    hr()
    print(f"Results: {len(passed)} passed, {len(failed)} failed")
    if passed:
        print(f"  ✓ {', '.join(passed)}")
    if failed:
        print(f"  ✗ {', '.join(failed)}")
    print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
