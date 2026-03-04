"""
Crawl4AI wrappers for scraping company websites.
All functions are wrapped in try/except — scraping failures are never fatal.

Before scraping, functions check for existing reports in the outputs/ directory
using fuzzy filename matching. If a qualified or research report already exists
for a company, the cached version is returned instead of hitting the website.
"""
import logging
import re
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Directories to search for cached company reports (relative to project root)
_OUTPUT_DIRS = ["outputs/qualified", "outputs/research"]


def _domain_to_slug(url: str) -> str:
    """Extract a normalised slug from a URL or domain string."""
    # Strip scheme and www
    slug = re.sub(r"^https?://", "", url.lower())
    slug = re.sub(r"^www\.", "", slug)
    # Keep only the domain part (drop path)
    slug = slug.split("/")[0]
    # Drop TLD and convert separators to spaces for matching
    slug = re.sub(r"\.(com|org|net|co|io|gov|edu)$", "", slug)
    slug = re.sub(r"[-_.]", " ", slug).strip()
    return slug


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_existing_report(company_url_or_name: str, threshold: float = 0.6) -> str:
    """
    Search outputs/qualified/ and outputs/research/ for an existing markdown
    report for this company. Uses fuzzy filename matching so slight name
    variations (e.g. 'jpmorgan' vs 'jp_morgan_chase') still resolve.

    Returns the file contents prefixed with a cache-hit banner if found,
    otherwise returns an empty string.
    """
    query_slug = _domain_to_slug(company_url_or_name)
    if not query_slug:
        return ""

    project_root = Path(__file__).parent.parent
    candidates: list[tuple[float, Path]] = []

    for dir_name in _OUTPUT_DIRS:
        output_dir = project_root / dir_name
        if not output_dir.exists():
            continue
        for md_file in output_dir.glob("*.md"):
            # Normalise the filename the same way
            file_slug = re.sub(r"[-_]", " ", md_file.stem)
            # Remove trailing stage suffixes (_qualified, _research)
            file_slug = re.sub(r"\s*(qualified|research)$", "", file_slug).strip()
            score = _fuzzy_score(query_slug, file_slug)
            if score >= threshold:
                candidates.append((score, md_file))

    if not candidates:
        return ""

    best_score, best_file = max(candidates, key=lambda t: t[0])
    try:
        content = best_file.read_text(encoding="utf-8")
        logger.info(
            f"find_existing_report: cache hit for '{query_slug}' → {best_file.name} "
            f"(score={best_score:.2f})"
        )
        return (
            f"> **[CACHED REPORT — {best_file.parent.name}/{best_file.name}]**  \n"
            f"> Loaded from existing output instead of re-scraping. "
            f"Match score: {best_score:.0%}\n\n"
            + content
        )
    except Exception as e:
        logger.warning(f"find_existing_report: could not read {best_file}: {e}")
        return ""

# Paths that signal CSR/ESG content
CSR_KEYWORDS = [
    "csr", "sustainability", "community", "giving", "responsibility",
    "foundation", "social-impact", "esg", "environment", "partnership",
    "volunteer", "nonprofit", "grant", "philanthrop", "impact",
    "cause", "purpose", "values", "mission", "citizenship",
]

# Common direct URL paths to try for CSR content — tried in order
CSR_URL_PATHS = [
    "/sustainability", "/responsibility", "/csr", "/esg",
    "/community", "/impact", "/foundation", "/giving",
    "/corporate-responsibility", "/social-impact", "/citizenship",
    "/purpose", "/values", "/about/sustainability", "/about/community",
    "/about/responsibility",
]

# Path fragments that indicate irrelevant pages — excluded from scrape_site
IRRELEVANT_PATH_FRAGMENTS = [
    "recipe", "product", "shop", "store", "cart", "checkout",
    "account", "login", "signup", "careers", "jobs", "press",
    "news", "blog", "article", "event", "location", "map",
    "search", "faq", "help", "support", "contact", "sitemap",
    "privacy", "terms", "legal", "cookie",
]


# Maximum characters returned per scraped page — keeps token costs predictable.
# At ~4 chars/token, 8000 chars ≈ 2000 tokens. Enough for any CSR summary.
_MAX_PAGE_CHARS = 8_000

# Maximum total characters returned by scrape_csr_pages across all pages.
_MAX_TOTAL_CHARS = 24_000


async def scrape_page(url: str, _retries: int = 1) -> str:
    """
    Scrape a single URL and return clean markdown text (capped at 8,000 chars).
    Use this to read a company's homepage, about page, or CSR/sustainability page.
    Retries once on failure (handles Playwright navigation race conditions).
    Returns empty string if both attempts fail — never raises.
    """
    import asyncio

    for attempt in range(1 + _retries):
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

            config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                word_count_threshold=50,
                remove_overlay_elements=True,
                process_iframes=False,
            )
            async with AsyncWebCrawler(headless=True) as crawler:
                result = await crawler.arun(url=url, config=config)
                if result.success:
                    content = getattr(result, "markdown_v2", None)
                    if content:
                        text = getattr(content, "fit_markdown", None) or str(content)
                    else:
                        text = result.markdown or ""
                    return text[:_MAX_PAGE_CHARS]
                if attempt < _retries:
                    logger.info(f"Retrying {url} (attempt {attempt + 2}/{1 + _retries})")
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"Scrape failed for {url}: {result.error_message}")
        except Exception as e:
            if attempt < _retries:
                logger.info(f"Retrying {url} after error: {e}")
                await asyncio.sleep(2)
            else:
                logger.warning(f"scrape_page error for {url}: {e}")
    return ""


async def scrape_csr_pages(domain: str, max_pages: int = 4) -> str:
    """
    Try common CSR/ESG URL paths for a company domain and return whatever has content.
    This is the recommended first tool when researching a company — it directly targets
    sustainability, responsibility, community, and foundation pages without crawling
    irrelevant pages like recipes, products, or store locators.

    IMPORTANT: Before scraping, this function checks outputs/qualified/ and
    outputs/research/ for an existing report on this company. If one is found
    (fuzzy name match ≥ 60%), the cached report is returned immediately — no
    web request is made. This prevents redundant scraping.

    Pass the bare domain, e.g. "wholefoodsmarket.com" or "goldmansachs.com".
    Returns concatenated markdown from all pages that returned content.
    Returns empty string if nothing found — never raises.
    """
    # Check for an existing report before hitting the web
    cached = find_existing_report(domain)
    if cached:
        return cached

    try:
        base = domain.rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"

        found = []
        total_chars = 0
        for path in CSR_URL_PATHS:
            if len(found) >= max_pages or total_chars >= _MAX_TOTAL_CHARS:
                break
            url = base + path
            content = await scrape_page(url)
            if len(content) > 300:
                found.append(f"### Page: {url}\n\n{content}")
                total_chars += len(content)
                logger.info(f"scrape_csr_pages: found content at {url} ({len(content)} chars)")

        combined = "\n\n---\n\n".join(found)
        return combined[:_MAX_TOTAL_CHARS]
    except Exception as e:
        logger.warning(f"scrape_csr_pages error for {domain}: {e}")
        return ""


async def scrape_site(base_url: str, max_pages: int = 5) -> str:
    """
    Crawl up to max_pages pages of a company website, prioritising CSR/ESG content.
    Only follows links that have at least one CSR keyword in their URL or link text.
    Skips irrelevant pages (recipes, products, store, cart, jobs, etc.).

    Use this only if scrape_csr_pages() returns too little content — for example,
    when a company uses non-standard URL paths for their CSR section.
    Returns empty string on failure — never raises.
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
        async with AsyncWebCrawler(headless=True) as crawler:
            result = await crawler.arun(url=base_url, config=config)
            if not result.success:
                return ""

            links = result.links.get("internal", []) if result.links else []

            def score_link(link: dict) -> int:
                href = (link.get("href") or "").lower()
                text = (link.get("text") or "").lower()
                # Hard exclude irrelevant paths
                if any(frag in href for frag in IRRELEVANT_PATH_FRAGMENTS):
                    return -1
                return sum(1 for kw in CSR_KEYWORDS if kw in href or kw in text)

            # Only keep links with at least 1 CSR keyword match
            scored = sorted(
                [lnk for lnk in links if score_link(lnk) > 0],
                key=score_link,
                reverse=True,
            )
            priority_urls = [base_url] + [
                lnk["href"] for lnk in scored[: max_pages - 1] if lnk.get("href")
            ]

            pages = []
            for url in priority_urls:
                content = await scrape_page(url)
                if len(content) > 200:
                    pages.append(f"### Page: {url}\n\n{content}")

            return "\n\n---\n\n".join(pages)
    except Exception as e:
        logger.warning(f"scrape_site error for {base_url}: {e}")
        return ""
