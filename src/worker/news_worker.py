#!/usr/bin/env python3
"""
Simplified News Worker

Fetches articles from stubbed sources and stores them in the database.
"""

import asyncio
import sqlite3
import argparse
import sys
from datetime import datetime, timezone
from typing import List, Set
from loguru import logger

from ..db.init_db import get_connection, init_db

# Configuration
POLL_INTERVAL = 30 * 60  # 30 minutes in seconds


class NewsWorker:
    """Simple news worker that fetches and stores articles"""
    
    def __init__(self):
        self.processed_urls: Set[str] = set()
        self.running = False
    
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
            
            cursor.execute(query, (
                article["title"],
                article["source"], 
                article["url"],
                article["published_at"].isoformat(),
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
        return stored_count
    
    async def run_single_fetch(self) -> int:
        """Run one fetch cycle"""
        logger.info("Running single fetch")
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


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="News Worker")
    parser.add_argument("--once", action="store_true", help="Run single fetch")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--show-all", action="store_true", help="Show all articles")
    parser.add_argument("--sources", action="store_true", help="Show sources summary")
    parser.add_argument("--clear", action="store_true", help="Clear database")
    
    args = parser.parse_args()
    
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")
    
    # Initialize database
    conn = get_connection()
    init_db(conn)
    conn.close()
    
    worker = NewsWorker()
    
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
            count = await worker.run_single_fetch()
            logger.info(f"Single fetch complete: {count} articles stored")
        else:
            await worker.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())