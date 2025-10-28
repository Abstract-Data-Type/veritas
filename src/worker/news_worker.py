#!/usr/bin/env python3
"""
Simplified News Worker

Fetches articles from stubbed sources and stores them in the database.
"""

import asyncio
import sqlite3
import argparse
import sys
import httpx
import feedparser
from datetime import datetime, timezone, timedelta
from typing import List, Set
from loguru import logger

from ..db.init_db import get_connection, init_db

# Configuration
POLL_INTERVAL = 30 * 60  # 30 minutes in seconds
DEFAULT_HOURS_BACK = 1  # Default to last 1 hour
DEFAULT_ARTICLE_LIMIT = 5  # Default limit of 5 articles


class NewsWorker:
    """Simple news worker that fetches and stores articles"""
    
    def __init__(self, hours_back: int = DEFAULT_HOURS_BACK, limit: int = DEFAULT_ARTICLE_LIMIT):
        self.processed_urls: Set[str] = set()
        self.running = False
        self.hours_back = hours_back
        self.limit = limit
    
    async def fetch_stubbed_articles(self) -> List[dict]:
        """Fetch articles from all stubbed sources"""
        logger.info("Fetching articles from stubbed sources")
        
        # Simulate fetch delay
        await asyncio.sleep(0.5)
        
        # Return stubbed articles from multiple sources
        articles = [
            {
                "title": "Breaking: Tech Giant Announces New AI Initiative",
                "source": "TechNews",
                "url": f"https://technews.com/ai-initiative-{datetime.now().timestamp()}",
                "raw_text": "Tech giant revealed plans for new AI initiative...",
                "published_at": datetime.now(timezone.utc)
            },
            {
                "title": "Global Climate Summit Reaches Historic Agreement",
                "source": "WorldNews", 
                "url": f"https://worldnews.com/climate-summit-{datetime.now().timestamp()}",
                "raw_text": "World leaders reached historic agreement on carbon reduction...",
                "published_at": datetime.now(timezone.utc)
            },
            {
                "title": "Stock Market Sees Record Gains",
                "source": "FinanceDaily",
                "url": f"https://financedaily.com/market-gains-{datetime.now().timestamp()}",
                "raw_text": "Stock market posted record gains amid economic recovery...",
                "published_at": datetime.now(timezone.utc)
            },
            {
                "title": "International Trade Negotiations Show Progress",
                "source": "Reuters",
                "url": f"https://reuters.com/trade-negotiations-{datetime.now().timestamp()}",
                "raw_text": "Trade negotiations between major economies showed progress...",
                "published_at": datetime.now(timezone.utc)
            }
        ]
        
        logger.info(f"Fetched {len(articles)} stubbed articles")
        return articles

    async def fetch_cnn_articles(self) -> List[dict]:
        """Fetch recent articles from CNN RSS feed"""
        logger.info(f"Fetching CNN articles from last {self.hours_back} hour(s), limit {self.limit}")
        
        try:
            # CNN RSS feed URL
            rss_url = "http://rss.cnn.com/rss/cnn_topstories.rss"
            
            # Rate limiting - be respectful
            await asyncio.sleep(1.0)
            
            # Fetch RSS feed with custom headers to avoid blocking
            logger.debug(f"Fetching RSS from: {rss_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml"
            }
            
            async with httpx.AsyncClient(
                timeout=30.0,
                verify=False,  # Skip SSL verification for testing
                follow_redirects=True
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
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.hours_back)
            
            articles = []
            for entry in feed.entries:
                # Stop if we've reached the limit
                if len(articles) >= self.limit:
                    break
                
                try:
                    # Parse publication date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    
                    # Skip articles older than cutoff
                    if published_at and published_at < cutoff_time:
                        logger.debug(f"Skipping old article: {entry.title} ({published_at})")
                        continue
                    
                    # Extract article data
                    article = {
                        "title": entry.title.strip() if hasattr(entry, 'title') else "No Title",
                        "source": "CNN",
                        "url": entry.link.strip() if hasattr(entry, 'link') else "",
                        "raw_text": entry.summary.strip() if hasattr(entry, 'summary') else "No content available",
                        "published_at": published_at or datetime.now(timezone.utc)
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
    
    def is_duplicate(self, conn: sqlite3.Connection, article: dict) -> bool:
        """Check if article already exists"""
        cursor = conn.cursor()
        
        # Check by URL
        cursor.execute("SELECT 1 FROM articles WHERE url = ?", (article["url"],))
        if cursor.fetchone():
            return True
        
        # Check in memory
        if article["url"] in self.processed_urls:
            return True
        
        return False
    
    def store_article(self, conn: sqlite3.Connection, article: dict) -> bool:
        """Store single article in database"""
        try:
            cursor = conn.cursor()
            
            query = """
            INSERT INTO articles (title, source, url, published_at, raw_text, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            # Handle None publication date with fallback
            published_at_str = (
                article["published_at"].isoformat() 
                if article["published_at"] 
                else datetime.now(timezone.utc).isoformat()
            )
            
            cursor.execute(query, (
                article["title"],
                article["source"], 
                article["url"],
                published_at_str,
                article["raw_text"]
            ))
            
            conn.commit()
            self.processed_urls.add(article["url"])
            
            logger.info(f"Stored: {article['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return False
    
    def process_articles(self, articles: List[dict]) -> int:
        """Process and store articles, return count stored"""
        if not articles:
            return 0
        
        conn = get_connection()
        stored_count = 0
        
        try:
            for article in articles:
                if not self.is_duplicate(conn, article):
                    if self.store_article(conn, article):
                        stored_count += 1
                else:
                    logger.debug(f"Duplicate skipped: {article['title']}")
        finally:
            conn.close()
        
        logger.info(f"Stored {stored_count}/{len(articles)} articles")
        
        # Prevent memory leak by cleaning up old URLs
        self.cleanup_memory()
        
        return stored_count
    
    async def run_single_fetch(self, use_cnn: bool = False) -> int:
        """Run one fetch cycle"""
        if use_cnn:
            logger.info("Running single fetch with CNN scraper")
            articles = await self.fetch_cnn_articles()
        else:
            logger.info("Running single fetch with stubbed articles")
            articles = await self.fetch_stubbed_articles()
        
        return self.process_articles(articles)
    
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
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT title, source, created_at 
                FROM articles 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent = cursor.fetchall()
            
            logger.info(f"=== Status ===")
            logger.info(f"Total articles: {total_articles}")
            logger.info(f"Running: {self.running}")
            
            if recent:
                logger.info("Recent articles:")
                for title, source, created_at in recent:
                    logger.info(f"  - {title} ({source})")
            
        finally:
            conn.close()
    
    def show_all_articles(self):
        """Show all articles with details"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT article_id, title, source, url, created_at 
                FROM articles 
                ORDER BY created_at DESC
            """)
            articles = cursor.fetchall()
            
            print(f"\n=== ALL ARTICLES ({len(articles)} total) ===")
            for article_id, title, source, url, created_at in articles:
                print(f"ID: {article_id}")
                print(f"Title: {title}")
                print(f"Source: {source}")
                print(f"URL: {url}")
                print(f"Created: {created_at}")
                print("-" * 50)
            
        finally:
            conn.close()
    
    def show_sources_summary(self):
        """Show summary by source"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source, COUNT(*) as count, MAX(created_at) as latest
                FROM articles 
                GROUP BY source 
                ORDER BY count DESC
            """)
            sources = cursor.fetchall()
            
            print(f"\n=== SOURCES SUMMARY ===")
            for source, count, latest in sources:
                print(f"{source}: {count} articles (latest: {latest})")
            
        finally:
            conn.close()
    
    def clear_database(self):
        """Clear all articles (for testing)"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM articles")
            conn.commit()
            self.processed_urls.clear()
            logger.info("Database cleared")
        finally:
            conn.close()
    
    def cleanup_memory(self, max_urls: int = 1000):
        """Clean up processed_urls to prevent memory leak"""
        if len(self.processed_urls) > max_urls:
            # Keep only the most recent half
            urls_to_keep = list(self.processed_urls)[-max_urls//2:]
            self.processed_urls = set(urls_to_keep)
            logger.info(f"Cleaned up processed URLs, kept {len(self.processed_urls)}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="News Worker")
    parser.add_argument("--once", action="store_true", help="Run single fetch")
    parser.add_argument("--cnn", action="store_true", help="Use CNN scraper instead of stubs")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS_BACK, help=f"Hours back to fetch (default: {DEFAULT_HOURS_BACK})")
    parser.add_argument("--limit", type=int, default=DEFAULT_ARTICLE_LIMIT, help=f"Max articles to fetch (default: {DEFAULT_ARTICLE_LIMIT})")
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
    conn = get_connection()
    init_db(conn)
    conn.close()
    
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
            count = await worker.run_single_fetch(use_cnn=args.cnn)
            logger.info(f"Single fetch complete: {count} articles stored")
        else:
            await worker.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())