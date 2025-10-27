import os
from typing import Dict, Any

class WorkerConfig:
    """Configuration for the news worker"""
    
    # Polling intervals in seconds
    DEFAULT_POLL_INTERVAL = 30 * 60  # 30 minutes
    NEWSAPI_POLL_INTERVAL = int(os.getenv("NEWSAPI_POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
    REUTERS_POLL_INTERVAL = int(os.getenv("REUTERS_POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
    RSS_POLL_INTERVAL = int(os.getenv("RSS_POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
    
    # API Keys
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "stub_key")
    
    # RSS Sources
    RSS_FEEDS = [
        "https://feeds.reuters.com/reuters/topNews",
        "https://rss.cnn.com/rss/edition.rss",
        "https://feeds.bbci.co.uk/news/rss.xml"
    ]
    
    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests
    MAX_RETRIES = 3
    
    @classmethod
    def get_source_config(cls) -> Dict[str, Any]:
        """Get configuration for all news sources"""
        return {
            "newsapi": {
                "interval": cls.NEWSAPI_POLL_INTERVAL,
                "api_key": cls.NEWSAPI_KEY
            },
            "reuters": {
                "interval": cls.REUTERS_POLL_INTERVAL
            },
            "rss": {
                "interval": cls.RSS_POLL_INTERVAL,
                "feeds": cls.RSS_FEEDS
            }
        }