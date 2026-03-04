"""
Crawl4AI wrappers for scraping company websites.
All functions are wrapped in try/except — scraping failures are never fatal.
"""
import logging

logger = logging.getLogger(__name__)

CSR_KEYWORDS = [
    "csr", "sustainability", "community", "giving", "responsibility",
    "foundation", "social-impact", "esg", "environment", "partnership",
    "volunteer", "nonprofit", "grant", "philanthrop", "impact",
]


async def scrape_page(url: str) -> str:
    """
    Scrape a single URL and return clean markdown text.
    Use this to read a company's homepage, about page, or CSR/sustainability page.
    Returns empty string on failure — never raises.
    """
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
            logger.warning(f"Scrape failed for {url}: {result.error_message}")
            return ""
    except Exception as e:
        logger.warning(f"scrape_page error for {url}: {e}")
        return ""


async def scrape_site(base_url: str, max_pages: int = 5) -> str:
    """
    Crawl up to max_pages pages of a company website, prioritising CSR/ESG content.
    Returns all page content concatenated as markdown. Use this when a company's
    sustainability or community content is spread across multiple pages.
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
                return sum(1 for kw in CSR_KEYWORDS if kw in href or kw in text)

            scored = sorted(links, key=score_link, reverse=True)
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
