import os
from typing import Any


class WorkerConfig:
    """Configuration for the news worker"""

    # Polling intervals in seconds
    DEFAULT_POLL_INTERVAL = 30 * 60  # 30 minutes
    NEWSAPI_POLL_INTERVAL = int(
        os.getenv("NEWSAPI_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
    )
    REUTERS_POLL_INTERVAL = int(
        os.getenv("REUTERS_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
    )
    RSS_POLL_INTERVAL = int(os.getenv("RSS_POLL_INTERVAL", DEFAULT_POLL_INTERVAL))

    # API Keys
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "stub_key")

    # RSS Sources - these are the default RSS feeds that work reliably
    RSS_FEEDS = [
        # "https://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.npr.org/1001/rss.xml",  # NPR News
        "http://feeds.foxnews.com/foxnews/politics",  # Fox News Latest Headlines
    ]

    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests
    MAX_RETRIES = 3

    @classmethod
    def get_source_config(cls) -> dict[str, Any]:
        """Get configuration for all news sources"""
        return {
            "newsapi": {
                "interval": cls.NEWSAPI_POLL_INTERVAL,
                "api_key": cls.NEWSAPI_KEY,
            },
            "reuters": {"interval": cls.REUTERS_POLL_INTERVAL},
            "rss": {"interval": cls.RSS_POLL_INTERVAL, "feeds": cls.RSS_FEEDS},
        }
