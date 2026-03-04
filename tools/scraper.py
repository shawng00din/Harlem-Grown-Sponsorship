"""
Crawl4AI wrappers for scraping company websites.
All functions are wrapped in try/except — scraping failures are never fatal.
"""
import logging

logger = logging.getLogger(__name__)

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


async def scrape_page(url: str, _retries: int = 1) -> str:
    """
    Scrape a single URL and return clean markdown text.
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
                        return getattr(content, "fit_markdown", None) or str(content)
                    return result.markdown or ""
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

    Pass the bare domain, e.g. "wholefoodsmarket.com" or "goldmansachs.com".
    Returns concatenated markdown from all pages that returned content.
    Returns empty string if nothing found — never raises.
    """
    try:
        base = domain.rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"

        found = []
        for path in CSR_URL_PATHS:
            if len(found) >= max_pages:
                break
            url = base + path
            content = await scrape_page(url)
            if len(content) > 300:
                found.append(f"### Page: {url}\n\n{content}")
                logger.info(f"scrape_csr_pages: found content at {url}")

        return "\n\n---\n\n".join(found)
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
