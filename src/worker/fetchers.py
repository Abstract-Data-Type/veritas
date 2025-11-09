import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
        published_at: Optional[datetime] = None,
        raw_text: str = "",
    ):
        self.title = title
        self.source = source
        self.url = url
        self.published_at = published_at or datetime.now(timezone.utc)
        self.raw_text = raw_text


class NewsAPIFetcher:
    """Stubbed NewsAPI integration"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"

    async def fetch_articles(self) -> List[ArticleData]:
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

    async def fetch_articles(self) -> List[ArticleData]:
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
    """RSS feed parser with stubbed functionality"""

    def __init__(self, feeds: List[str]):
        self.feeds = feeds

    async def fetch_articles(self) -> List[ArticleData]:
        """Fetch articles from RSS feeds (stubbed)"""
        logger.info(f"Fetching articles from {len(self.feeds)} RSS feeds (stubbed)")

        all_articles = []

        for feed_url in self.feeds:
            logger.info(f"Processing RSS feed: {feed_url}")

            # Simulate RSS parsing delay
            await asyncio.sleep(0.2)

            # Stubbed RSS data
            feed_articles = [
                ArticleData(
                    title=f"RSS Article from {feed_url.split('//')[1].split('/')[0]}",
                    source=feed_url.split("//")[1].split("/")[0],
                    url=f"{feed_url}/article-{hash(feed_url) % 1000}",
                    raw_text="This is a stubbed RSS article content from the feed...",
                )
            ]

            all_articles.extend(feed_articles)

        logger.info(f"RSS feeds returned {len(all_articles)} total articles")
        return all_articles


class NewsFetcher:
    """Main news fetcher that coordinates all sources"""

    def __init__(self):
        config = WorkerConfig.get_source_config()

        self.newsapi_fetcher = NewsAPIFetcher(config["newsapi"]["api_key"])
        self.reuters_fetcher = ReutersFetcher()
        self.rss_fetcher = RSSFetcher(config["rss"]["feeds"])

    async def fetch_all_sources(self) -> List[ArticleData]:
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
