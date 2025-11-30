#!/usr/bin/env python3
"""
Simplified News Worker

Fetches articles from stubbed sources and stores them in the database.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import feedparser
import httpx
from loguru import logger
from newsapi import NewsApiClient
from sqlalchemy.orm import Session

from ..ai import rate_bias
from ..db.init_db import get_connection, init_db
from ..models.bias_rating import normalize_score_to_range
from ..models.sqlalchemy_models import Article, BiasRating

# Configuration
POLL_INTERVAL = 30 * 60  # 30 minutes in seconds
DEFAULT_HOURS_BACK = 1  # Default to last 1 hour
DEFAULT_ARTICLE_LIMIT = 5  # Default limit of 5 articles


class NewsWorker:
    """Simple news worker that fetches and stores articles"""

    def __init__(
        self, hours_back: int = DEFAULT_HOURS_BACK, limit: int = DEFAULT_ARTICLE_LIMIT
    ):
        self.processed_urls: set[str] = set()
        self.running = False
        self.hours_back = hours_back
        self.limit = limit

    async def fetch_stubbed_articles(self) -> list[dict]:
        """Fetch articles from all stubbed sources - DEPRECATED, use fetch_rss_articles instead"""
        logger.warning("Using deprecated stubbed articles - these URLs are not real!")
        logger.info("Fetching articles from stubbed sources")

        # Simulate fetch delay
        await asyncio.sleep(0.5)

        # Return stubbed articles - NOTE: These URLs are fake and for testing only
        articles = [
            {
                "title": "Breaking: Tech Giant Announces New AI Initiative",
                "source": "TechNews (Stub)",
                "url": f"https://example.com/stub/ai-initiative-{datetime.now().timestamp()}",
                "raw_text": "Tech giant revealed plans for new AI initiative...",
                "published_at": datetime.now(UTC),
            },
            {
                "title": "Global Climate Summit Reaches Historic Agreement",
                "source": "WorldNews (Stub)",
                "url": f"https://example.com/stub/climate-summit-{datetime.now().timestamp()}",
                "raw_text": "World leaders reached historic agreement on carbon reduction...",
                "published_at": datetime.now(UTC),
            },
        ]

        logger.info(f"Fetched {len(articles)} stubbed articles")
        return articles

    async def fetch_rss_articles(self) -> list[dict]:
        """Fetch articles from configured RSS feeds"""
        from .config import WorkerConfig
        from .fetchers import RSSFetcher

        logger.info(f"Fetching articles from RSS feeds, limit {self.limit}")

        try:
            fetcher = RSSFetcher(WorkerConfig.RSS_FEEDS, limit_per_feed=self.limit)
            article_data_list = await fetcher.fetch_articles()

            # Convert ArticleData objects to dict format
            articles = []
            for article_data in article_data_list:
                articles.append({
                    "title": article_data.title,
                    "source": article_data.source,
                    "url": article_data.url,
                    "raw_text": article_data.raw_text,
                    "published_at": article_data.published_at,
                })

            logger.info(f"Fetched {len(articles)} RSS articles")
            return articles

        except Exception as e:
            logger.error(f"Error fetching RSS feeds: {e}")
            return []

    async def fetch_cnn_articles(self) -> list[dict]:
        """Fetch recent articles from CNN RSS feed"""
        logger.info(
            f"Fetching CNN articles from last {self.hours_back} hour(s), limit {self.limit}"
        )

        try:
            # CNN RSS feed URL
            rss_url = "http://rss.cnn.com/rss/cnn_topstories.rss"

            # Rate limiting - be respectful
            await asyncio.sleep(1.0)

            # Fetch RSS feed with custom headers to avoid blocking
            logger.debug(f"Fetching RSS from: {rss_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml",
            }

            async with httpx.AsyncClient(
                timeout=30.0,
                verify=False,  # Skip SSL verification for testing
                follow_redirects=True,
            ) as client:
                response = await client.get(rss_url, headers=headers)
                logger.debug(f"HTTP response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                response.raise_for_status()

            # Parse RSS feed
            logger.debug(f"Response content length: {len(response.text)}")
            logger.debug(f"Response content preview: {response.text[:200]}...")
            feed = feedparser.parse(response.text)
            logger.debug(f"Feedparser found {len(feed.entries)} entries")

            if not feed.entries:
                logger.warning("No entries found in CNN RSS feed")
                return []

            # Calculate cutoff time
            cutoff_time = datetime.now(UTC) - timedelta(hours=self.hours_back)

            articles = []
            for entry in feed.entries:
                # Stop if we've reached the limit
                if len(articles) >= self.limit:
                    break

                try:
                    # Parse publication date
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(
                            *entry.published_parsed[:6], tzinfo=UTC
                        )

                    # Skip articles older than cutoff
                    if published_at and published_at < cutoff_time:
                        logger.debug(
                            f"Skipping old article: {entry.title} ({published_at})"
                        )
                        continue

                    # Extract article data
                    article = {
                        "title": (
                            entry.title.strip()
                            if hasattr(entry, "title")
                            else "No Title"
                        ),
                        "source": "CNN",
                        "url": entry.link.strip() if hasattr(entry, "link") else "",
                        "raw_text": (
                            entry.summary.strip()
                            if hasattr(entry, "summary")
                            else "No content available"
                        ),
                        "published_at": published_at or datetime.now(UTC),
                    }

                    # Skip if no URL
                    if not article["url"]:
                        continue

                    articles.append(article)
                    logger.debug(f"Added article: {article['title']}")

                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} recent CNN articles")
            return articles

        except Exception as e:
            logger.error(f"Error fetching CNN RSS feed: {e}")
            return []

    async def fetch_newsapi_headlines(self) -> list[dict]:
        """Fetch top headlines from NewsAPI for US in English"""
        logger.info(f"Fetching NewsAPI headlines, limit {self.limit}")

        try:
            # Get API key from environment
            api_key = os.getenv("NEWSCLIENT_API_KEY")
            if not api_key:
                logger.error("NEWSCLIENT_API_KEY environment variable not set")
                return []

            # Initialize NewsAPI client
            newsapi = NewsApiClient(api_key=api_key)

            # Rate limiting - be respectful to API
            await asyncio.sleep(1.0)

            # Fetch top headlines for US in English
            logger.debug(f"Fetching US headlines with limit {self.limit}")
            response = newsapi.get_top_headlines(
                country="us",
                language="en",
                page_size=min(self.limit, 100),  # API max is 100
            )

            if response["status"] != "ok":
                logger.error(
                    f"NewsAPI error: {response.get('message', 'Unknown error')}"
                )
                return []

            articles_data = response.get("articles", [])
            logger.debug(f"NewsAPI returned {len(articles_data)} articles")

            if not articles_data:
                logger.warning("No articles returned from NewsAPI")
                return []

            # Transform articles to our format
            articles = []
            for article_data in articles_data:
                try:
                    # Parse publication date
                    published_at = None
                    if article_data.get("publishedAt"):
                        # NewsAPI returns ISO format: "2023-12-01T10:30:00Z"
                        published_at = datetime.fromisoformat(
                            article_data["publishedAt"].replace("Z", "+00:00")
                        )

                    # Map to our article format
                    article = {
                        "title": article_data.get("title", "No Title").strip(),
                        "source": article_data.get("source", {}).get("name", "NewsAPI"),
                        "url": article_data.get("url", "").strip(),
                        "raw_text": article_data.get(
                            "description", "No description available"
                        ).strip(),
                        "published_at": published_at or datetime.now(UTC),
                    }

                    # Skip if no URL
                    if not article["url"]:
                        logger.debug("Skipping article with no URL")
                        continue

                    articles.append(article)
                    logger.debug(f"Added NewsAPI article: {article['title']}")

                except Exception as e:
                    logger.error(f"Error parsing NewsAPI article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} NewsAPI headlines")
            return articles

        except Exception as e:
            logger.error(f"Error fetching NewsAPI headlines: {e}")
            return []

    def is_duplicate(self, db: Session, article: dict) -> bool:
        """Check if article already exists"""
        # Check by URL in database
        existing = db.query(Article).filter(Article.url == article["url"]).first()
        if existing:
            return True

        # Check in memory
        if article["url"] in self.processed_urls:
            return True

        return False

    def store_article(self, db: Session, article: dict) -> int | None:
        """Store single article in database and return article_id"""
        try:
            # Handle None publication date with fallback
            published_at = (
                article["published_at"]
                if article["published_at"]
                else datetime.now(UTC)
            )

            new_article = Article(
                title=article["title"],
                source=article["source"],
                url=article["url"],
                published_at=published_at,
                raw_text=article["raw_text"],
                created_at=datetime.now(UTC),
            )

            db.add(new_article)
            db.commit()
            db.refresh(new_article)  # Refresh to get the article_id
            self.processed_urls.add(article["url"])

            logger.info(f"Stored: {article['title']} (ID: {new_article.article_id})")
            return new_article.article_id

        except Exception as e:
            logger.error(f"Error storing article: {e}")
            db.rollback()
            return None

    async def analyze_article_bias(self, db: Session, article_id: int, raw_text: str) -> bool:
        """Analyze bias for an article and store the rating"""
        try:
            if not raw_text or len(raw_text.strip()) < 50:
                logger.debug(f"Article {article_id} text too short for bias analysis")
                return False

            logger.info(f"Analyzing bias for article {article_id}")
            bias_result = await rate_bias(raw_text)

            # Extract scores from result
            scores = bias_result.get("scores", {})

            # Extract individual dimension scores (on 1-7 scale)
            partisan_bias = scores.get("partisan_bias")
            affective_bias = scores.get("affective_bias")
            framing_bias = scores.get("framing_bias")
            sourcing_bias = scores.get("sourcing_bias")

            # Calculate overall bias score as average of dimensions, then normalize to -1 to 1
            valid_scores = [s for s in [partisan_bias, affective_bias, framing_bias, sourcing_bias] if s is not None]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                overall_bias_score = normalize_score_to_range(avg_score)  # Convert 1-7 to -1 to 1
            else:
                overall_bias_score = None

            # Store the bias rating
            new_rating = BiasRating(
                article_id=article_id,
                bias_score=overall_bias_score,
                partisan_bias=partisan_bias,
                affective_bias=affective_bias,
                framing_bias=framing_bias,
                sourcing_bias=sourcing_bias,
                reasoning=None,
                evaluated_at=datetime.now(UTC),
            )

            db.add(new_rating)
            db.commit()

            logger.info(
                f"Stored bias rating for article {article_id}: "
                f"overall={overall_bias_score}, partisan={partisan_bias}, "
                f"affective={affective_bias}, framing={framing_bias}, sourcing={sourcing_bias}"
            )
            return True

        except Exception as e:
            logger.error(f"Error analyzing bias for article {article_id}: {e}")
            db.rollback()
            return False

    async def process_articles(self, articles: list[dict]) -> int:
        """Process and store articles with bias analysis, return count stored"""
        if not articles:
            return 0

        with get_connection() as db:
            stored_count = 0

            try:
                for article in articles:
                    if not self.is_duplicate(db, article):
                        article_id = self.store_article(db, article)
                        if article_id:
                            stored_count += 1
                            # Analyze bias for the newly stored article
                            await self.analyze_article_bias(db, article_id, article.get("raw_text", ""))
                    else:
                        logger.debug(f"Duplicate skipped: {article['title']}")
            except Exception as e:
                logger.error(f"Error processing articles: {e}")

        logger.info(f"Stored {stored_count}/{len(articles)} articles")

        # Prevent memory leak by cleaning up old URLs
        self.cleanup_memory()

        return stored_count

    async def run_single_fetch(
        self, use_cnn: bool = False, use_newsapi: bool = False, use_stub: bool = False
    ) -> int:
        """Run one fetch cycle"""
        if use_newsapi:
            logger.info("Running single fetch with NewsAPI")
            articles = await self.fetch_newsapi_headlines()
        elif use_cnn:
            logger.info("Running single fetch with CNN scraper")
            articles = await self.fetch_cnn_articles()
        elif use_stub:
            logger.info("Running single fetch with stubbed articles (testing only)")
            articles = await self.fetch_stubbed_articles()
        else:
            logger.info("Running single fetch with RSS feeds")
            articles = await self.fetch_rss_articles()

        return await self.process_articles(articles)

    async def run_scheduler(self):
        """Run continuous scheduler"""
        logger.info(f"Starting scheduler (interval: {POLL_INTERVAL}s)")
        self.running = True

        while self.running:
            try:
                stored_count = await self.run_single_fetch()
                logger.info(f"Fetch cycle complete: {stored_count} articles stored")

                # Wait for next cycle
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        logger.info("Scheduler stopped")

    def stop(self):
        """Stop the scheduler"""
        self.running = False

    def show_status(self):
        """Show current status"""
        with get_connection() as db:
            try:
                total_articles = db.query(Article).count()

                recent = (
                    db.query(Article.title, Article.source, Article.created_at)
                    .order_by(Article.created_at.desc())
                    .limit(5)
                    .all()
                )

                logger.info("=== Status ===")
                logger.info(f"Total articles: {total_articles}")
                logger.info(f"Running: {self.running}")

                if recent:
                    logger.info("Recent articles:")
                    for title, source, created_at in recent:
                        logger.info(f"  - {title} ({source})")
            except Exception as e:
                logger.error(f"Error showing status: {e}")

    def show_all_articles(self):
        """Show all articles with details"""
        with get_connection() as db:
            try:
                articles = (
                    db.query(
                        Article.article_id,
                        Article.title,
                        Article.source,
                        Article.url,
                        Article.created_at,
                    )
                    .order_by(Article.created_at.desc())
                    .all()
                )

                print(f"\n=== ALL ARTICLES ({len(articles)} total) ===")
                for article_id, title, source, url, created_at in articles:
                    print(f"ID: {article_id}")
                    print(f"Title: {title}")
                    print(f"Source: {source}")
                    print(f"URL: {url}")
                    print(f"Created: {created_at}")
                    print("-" * 50)
            except Exception as e:
                logger.error(f"Error showing articles: {e}")

    def show_sources_summary(self):
        """Show summary by source"""
        with get_connection() as db:
            try:
                from sqlalchemy import func

                sources = (
                    db.query(
                        Article.source,
                        func.count(Article.article_id).label("count"),
                        func.max(Article.created_at).label("latest"),
                    )
                    .group_by(Article.source)
                    .order_by(func.count(Article.article_id).desc())
                    .all()
                )

                print("\n=== SOURCES SUMMARY ===")
                for source, count, latest in sources:
                    print(f"{source}: {count} articles (latest: {latest})")
            except Exception as e:
                logger.error(f"Error showing sources summary: {e}")

    def clear_database(self):
        """Clear all articles (for testing)"""
        with get_connection() as db:
            try:
                db.query(Article).delete()
                db.commit()
                self.processed_urls.clear()
                logger.info("Database cleared")
            except Exception as e:
                logger.error(f"Error clearing database: {e}")
                db.rollback()

    def cleanup_memory(self, max_urls: int = 1000):
        """Clean up processed_urls to prevent memory leak"""
        if len(self.processed_urls) > max_urls:
            # Keep only the most recent half
            urls_to_keep = list(self.processed_urls)[-max_urls // 2 :]
            self.processed_urls = set(urls_to_keep)
            logger.info(f"Cleaned up processed URLs, kept {len(self.processed_urls)}")


async def main():
    """Main entry point"""
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    parser = argparse.ArgumentParser(description="News Worker")
    parser.add_argument("--once", action="store_true", help="Run single fetch")
    parser.add_argument(
        "--cnn", action="store_true", help="Use CNN scraper instead of stubs"
    )
    parser.add_argument(
        "--newsapi", action="store_true", help="Use NewsAPI for headlines"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=DEFAULT_HOURS_BACK,
        help=f"Hours back to fetch (default: {DEFAULT_HOURS_BACK})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_ARTICLE_LIMIT,
        help=f"Max articles to fetch (default: {DEFAULT_ARTICLE_LIMIT})",
    )
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--show-all", action="store_true", help="Show all articles")
    parser.add_argument("--sources", action="store_true", help="Show sources summary")
    parser.add_argument("--clear", action="store_true", help="Clear database")

    args = parser.parse_args()

    # Setup logging
    logger.remove()
    log_level = "DEBUG" if args.cnn else "INFO"  # More verbose for CNN debugging
    logger.add(sys.stderr, level=log_level, format="{time} | {level} | {message}")

    # Initialize database
    init_db()

    worker = NewsWorker(hours_back=args.hours, limit=args.limit)

    try:
        if args.status:
            worker.show_status()
        elif args.show_all:
            worker.show_all_articles()
        elif args.sources:
            worker.show_sources_summary()
        elif args.clear:
            worker.clear_database()
        elif args.once:
            count = await worker.run_single_fetch(
                use_cnn=args.cnn, use_newsapi=args.newsapi
            )
            logger.info(f"Single fetch complete: {count} articles stored")
        else:
            await worker.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
