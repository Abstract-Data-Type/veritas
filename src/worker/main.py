#!/usr/bin/env python3
"""
News Worker Entry Point

This script runs the scheduled news worker that fetches articles from multiple sources
and stores them in the database.

Usage:
    python -m src.worker.main              # Run scheduler
    python -m src.worker.main --once       # Run single fetch
    python -m src.worker.main --status     # Check status
"""

import asyncio
import argparse
import signal
import sys
from loguru import logger

from .scheduler import JobScheduler
from ..db.init_db import init_db, get_connection


class NewsWorker:
    """Main news worker application"""
    
    def __init__(self):
        self.scheduler = JobScheduler()
        self.shutdown_event = asyncio.Event()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler():
            logger.info("Received shutdown signal")
            self.shutdown_event.set()
        
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
    
    async def run_scheduler(self):
        """Run the scheduled worker"""
        logger.info("Starting news worker scheduler")
        
        # Initialize database
        self.ensure_database()
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        try:
            # Start scheduler
            scheduler_task = asyncio.create_task(self.scheduler.start())
            
            # Wait for shutdown signal or scheduler completion
            done, pending = await asyncio.wait(
                [scheduler_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            
            # Stop scheduler gracefully
            await self.scheduler.stop()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error running scheduler: {e}")
        finally:
            logger.info("News worker shutdown complete")
    
    async def run_single_fetch(self):
        """Run a single fetch operation"""
        logger.info("Running single fetch operation")
        
        # Initialize database
        self.ensure_database()
        
        try:
            stored_ids = await self.scheduler.run_single_fetch()
            logger.info(f"Single fetch complete: {len(stored_ids)} articles stored")
            
            # Show recent articles
            recent = self.scheduler.pipeline.get_recent_articles(10)
            if recent:
                logger.info("Recent articles:")
                for article in recent:
                    logger.info(f"  - {article['title']} ({article['source']})")
            
            return stored_ids
            
        except Exception as e:
            logger.error(f"Error in single fetch: {e}")
            return []
    
    def get_status(self):
        """Get and display current status"""
        logger.info("Getting worker status")
        
        # Initialize database
        self.ensure_database()
        
        status = self.scheduler.get_status()
        
        logger.info("=== News Worker Status ===")
        logger.info(f"Running: {status['running']}")
        logger.info(f"Active tasks: {status['active_tasks']}")
        logger.info(f"Total articles: {status['article_count']}")
        
        if status['recent_articles']:
            logger.info("Recent articles:")
            for article in status['recent_articles']:
                logger.info(f"  - {article['title']} ({article['source']})")
        else:
            logger.info("No articles found")
        
        return status
    
    def ensure_database(self):
        """Ensure database is initialized"""
        try:
            conn = get_connection()
            init_db(conn)
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="News Worker")
    parser.add_argument("--once", action="store_true", help="Run single fetch and exit")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level, format="{time} | {level} | {message}")
    
    worker = NewsWorker()
    
    try:
        if args.status:
            worker.get_status()
        elif args.once:
            await worker.run_single_fetch()
        else:
            await worker.run_scheduler()
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())