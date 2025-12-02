import asyncio
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx
from loguru import logger

from .config import WorkerConfig


class ArticleData:
    """Data structure for raw article information"""

    def __init__(
        self,
        title: str,
        source: str,
        url: str,
        published_at: datetime | None = None,
        raw_text: str = "",
    ):
        self.title = title
        self.source = source
        self.url = url
        self.published_at = published_at or datetime.now(UTC)
        self.raw_text = raw_text


class NewsAPIFetcher:
    """Stubbed NewsAPI integration"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"

    async def fetch_articles(self) -> list[ArticleData]:
        """Fetch articles from NewsAPI (stubbed)"""
        logger.info("Fetching articles from NewsAPI (stubbed)")

        # Simulate API delay
        await asyncio.sleep(0.5)

        # Return stubbed data
        stubbed_articles = [
            ArticleData(
                title="Breaking: Tech Giant Announces New AI Initiative",
                source="TechNews",
                url="https://technews.com/ai-initiative-123",
                raw_text="In a major announcement today, the tech giant revealed plans for a new artificial intelligence initiative...",
            ),
            ArticleData(
                title="Global Climate Summit Reaches Historic Agreement",
                source="WorldNews",
                url="https://worldnews.com/climate-summit-456",
                raw_text="World leaders gathered at the climate summit have reached a historic agreement on carbon reduction targets...",
            ),
            ArticleData(
                title="Stock Market Sees Record Gains Amid Economic Recovery",
                source="FinanceDaily",
                url="https://financedaily.com/market-gains-789",
                raw_text="The stock market posted record gains today as investors showed confidence in the ongoing economic recovery...",
            ),
        ]

        logger.info(f"NewsAPI returned {len(stubbed_articles)} articles")
        return stubbed_articles


class ReutersFetcher:
    """Stubbed Reuters API integration"""

    async def fetch_articles(self) -> list[ArticleData]:
        """Fetch articles from Reuters (stubbed)"""
        logger.info("Fetching articles from Reuters (stubbed)")

        # Simulate API delay
        await asyncio.sleep(0.3)

        # Return stubbed data
        stubbed_articles = [
            ArticleData(
                title="International Trade Negotiations Show Progress",
                source="Reuters",
                url="https://reuters.com/trade-negotiations-abc",
                raw_text="International trade negotiations between major economies showed significant progress this week...",
            ),
            ArticleData(
                title="Healthcare Innovation Breakthrough Announced",
                source="Reuters",
                url="https://reuters.com/healthcare-breakthrough-def",
                raw_text="Researchers announced a breakthrough in healthcare innovation that could transform patient treatment...",
            ),
        ]

        logger.info(f"Reuters returned {len(stubbed_articles)} articles")
        return stubbed_articles


class RSSFetcher:
    """RSS feed parser that fetches real articles from RSS feeds"""

    def __init__(self, feeds: list[str], limit_per_feed: int = 5):
        self.feeds = feeds
        self.limit_per_feed = limit_per_feed

    async def fetch_articles(self) -> list[ArticleData]:
        """Fetch articles from RSS feeds"""
        logger.info(f"Fetching articles from {len(self.feeds)} RSS feeds")

        all_articles = []

        for feed_url in self.feeds:
            try:
                articles = await self._fetch_single_feed(feed_url)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {e}")
                continue

        logger.info(f"RSS feeds returned {len(all_articles)} total articles")
        return all_articles

    async def _fetch_single_feed(self, feed_url: str) -> list[ArticleData]:
        """Fetch articles from a single RSS feed"""
        logger.info(f"Processing RSS feed: {feed_url}")

        # Rate limiting - be respectful
        await asyncio.sleep(0.5)

        try:
            # Fetch RSS feed with custom headers to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }

            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(feed_url, headers=headers)
                response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.text)

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {feed_url}")
                return []

            # Extract source name from feed URL
            source_name = self._extract_source_name(feed_url, feed)

            articles = []
            for entry in feed.entries[: self.limit_per_feed]:
                try:
                    article = self._parse_entry(entry, source_name)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from {feed_url}")
            return articles

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching RSS feed {feed_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing RSS feed {feed_url}: {e}")
            return []

    def _extract_source_name(self, feed_url: str, feed: Any) -> str:
        """Extract a readable source name from feed metadata or URL"""
        # Try to get title from feed metadata
        if hasattr(feed, "feed") and hasattr(feed.feed, "title") and feed.feed.title:
            return feed.feed.title

        # Extract domain name as fallback
        try:
            from urllib.parse import urlparse

            parsed = urlparse(feed_url)
            domain = parsed.netloc
            # Remove www. prefix and common suffixes
            domain = domain.replace("www.", "").replace("feeds.", "").replace("rss.", "")
            # Get the main part of the domain
            parts = domain.split(".")
            if len(parts) >= 2:
                return parts[-2].capitalize()
            return domain.capitalize()
        except Exception:
            return "RSS Feed"

    def _parse_entry(self, entry: Any, source_name: str) -> ArticleData | None:
        """Parse a single RSS entry into ArticleData"""
        # Extract URL - this is the most important field
        url = None
        if hasattr(entry, "link") and entry.link:
            url = entry.link.strip()
        elif hasattr(entry, "id") and entry.id and entry.id.startswith("http"):
            url = entry.id.strip()

        if not url:
            logger.debug(f"Skipping entry without URL: {getattr(entry, 'title', 'No title')}")
            return None

        # Extract title
        title = "No Title"
        if hasattr(entry, "title") and entry.title:
            title = entry.title.strip()

        # Extract content/summary
        raw_text = ""
        if hasattr(entry, "summary") and entry.summary:
            raw_text = entry.summary.strip()
        elif hasattr(entry, "description") and entry.description:
            raw_text = entry.description.strip()
        elif hasattr(entry, "content") and entry.content:
            # Content is usually a list
            raw_text = entry.content[0].get("value", "").strip() if entry.content else ""

        # Parse publication date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                # published_parsed is a time.struct_time, use first 6 elements
                published_at = datetime(
                    entry.published_parsed[0],  # year
                    entry.published_parsed[1],  # month
                    entry.published_parsed[2],  # day
                    entry.published_parsed[3],  # hour
                    entry.published_parsed[4],  # minute
                    entry.published_parsed[5],  # second
                    tzinfo=UTC
                )
            except Exception:
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published_at = datetime(
                    entry.updated_parsed[0],  # year
                    entry.updated_parsed[1],  # month
                    entry.updated_parsed[2],  # day
                    entry.updated_parsed[3],  # hour
                    entry.updated_parsed[4],  # minute
                    entry.updated_parsed[5],  # second
                    tzinfo=UTC
                )
            except Exception:
                pass

        if not published_at:
            published_at = datetime.now(UTC)

        return ArticleData(
            title=title,
            source=source_name,
            url=url,
            published_at=published_at,
            raw_text=raw_text or "No content available",
        )


class NewsFetcher:
    """Main news fetcher that coordinates all sources"""

    def __init__(self):
        config = WorkerConfig.get_source_config()

        self.newsapi_fetcher = NewsAPIFetcher(config["newsapi"]["api_key"])
        self.reuters_fetcher = ReutersFetcher()
        self.rss_fetcher = RSSFetcher(config["rss"]["feeds"])

    async def fetch_all_sources(self) -> list[ArticleData]:
        """Fetch articles from all configured sources"""
        logger.info("Starting fetch from all news sources")

        all_articles = []

        try:
            # Fetch from all sources concurrently
            tasks = [
                self.newsapi_fetcher.fetch_articles(),
                self.reuters_fetcher.fetch_articles(),
                self.rss_fetcher.fetch_articles(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching from source {i}: {result}")
                else:
                    all_articles.extend(result)

            logger.info(f"Total articles fetched: {len(all_articles)}")
            return all_articles

        except Exception as e:
            logger.error(f"Error in fetch_all_sources: {e}")
            return []
