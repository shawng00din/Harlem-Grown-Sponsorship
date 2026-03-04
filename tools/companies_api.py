"""
The Companies API wrapper for structured firmographic data.
Falls back to curated_seed_list.json if API key is missing or credits exhausted.
"""
import json
import logging
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)

TARGET_SECTORS = [
    "Food & Beverage", "Healthcare", "Financial Services", "Insurance",
    "Retail", "Technology", "Real Estate", "Media & Entertainment",
    "Consumer Goods", "Pharmaceuticals", "Banking",
]


async def search_companies(
    city: str = "New York",
    industries: list[str] | None = None,
    min_employees: int = 200,
    limit: int = 50,
) -> list[dict]:
    """
    Search for companies matching the given filters.
    Returns a list of dicts: {name, domain, industry, employee_count, city, state, revenue_range}.
    Filters default to NYC metro, target HG sectors, 200+ employees.
    Falls back to the curated seed list if the API is unavailable.
    """
    if settings.COMPANIES_API_KEY:
        try:
            return await _search_via_api(city, industries, min_employees, limit)
        except Exception as e:
            logger.warning(f"Companies API failed: {e}. Falling back to seed list.")

    return _load_seed_list(city=city, industries=industries, min_employees=min_employees, limit=limit)


async def get_company_details(domain: str) -> dict | None:
    """
    Get detailed firmographic data for a single company by its domain name.
    Returns dict with HQ location, employee count, industry, and revenue range.
    Returns None if the company is not found or the API is unavailable.
    """
    if not settings.COMPANIES_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, verify=False, timeout=20.0
        ) as client:
            resp = await client.get(
                f"{settings.COMPANIES_API_BASE_URL}/companies/{domain}",
                headers={"Authorization": f"Bearer {settings.COMPANIES_API_KEY}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "name": data.get("name", ""),
                    "domain": domain,
                    "industry": data.get("industry", ""),
                    "employee_count": data.get("employees", 0),
                    "city": data.get("city", ""),
                    "state": data.get("state", ""),
                    "revenue_range": data.get("revenue", ""),
                }
    except Exception as e:
        logger.warning(f"get_company_details failed for {domain}: {e}")
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _search_via_api(
    city: str, industries: list[str] | None, min_employees: int, limit: int
) -> list[dict]:
    params: dict = {
        "city": city,
        "minEmployees": min_employees,
        "limit": limit,
    }
    if industries:
        params["industries"] = ",".join(industries)

    async with httpx.AsyncClient(
        follow_redirects=True, verify=False, timeout=30.0
    ) as client:
        resp = await client.get(
            f"{settings.COMPANIES_API_BASE_URL}/companies",
            params=params,
            headers={"Authorization": f"Bearer {settings.COMPANIES_API_KEY}"},
        )
        resp.raise_for_status()
        companies = resp.json().get("companies", [])

    return [
        {
            "name": c.get("name", ""),
            "domain": c.get("domain", ""),
            "industry": c.get("industry", ""),
            "employee_count": c.get("employees", 0),
            "city": c.get("city", ""),
            "state": c.get("state", ""),
            "revenue_range": c.get("revenue", ""),
        }
        for c in companies
    ]


def _load_seed_list(
    city: str,
    industries: list[str] | None,
    min_employees: int,
    limit: int,
) -> list[dict]:
    seed_path = Path(settings.SEED_LIST_PATH)
    if not seed_path.exists():
        logger.warning(f"Seed list not found at {seed_path}")
        return []

    all_companies: list[dict] = json.loads(seed_path.read_text(encoding="utf-8"))

    filtered = []
    city_lower = city.lower()
    industry_lower = [i.lower() for i in (industries or [])]

    for c in all_companies:
        if city_lower and city_lower not in (c.get("city") or "").lower():
            continue
        if industry_lower:
            if not any(i in (c.get("industry") or "").lower() for i in industry_lower):
                continue
        if c.get("employee_count", 0) < min_employees:
            continue
        filtered.append(c)

    return filtered[:limit]
