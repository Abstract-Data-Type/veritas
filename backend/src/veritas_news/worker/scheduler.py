import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from .config import WorkerConfig
from .fetchers import NewsFetcher
from .pipeline import ArticlePipeline


class JobScheduler:
    """Async job scheduler for news fetching tasks"""

    def __init__(self):
        self.config = WorkerConfig.get_source_config()
        self.fetcher = NewsFetcher()
        self.pipeline = ArticlePipeline()
        self.running = False
        self.tasks: dict[str, asyncio.Task] = {}

    async def _run_fetch_job(self, job_name: str, interval: int):
        """Run a single fetch job with retry logic"""
        logger.info(f"Starting job: {job_name} (interval: {interval}s)")

        while self.running:
            try:
                start_time = datetime.now()
                logger.info(f"Executing {job_name} fetch job")

                # Fetch articles from all sources
                articles = await self.fetcher.fetch_all_sources()

                if articles:
                    # Process and store articles
                    stored_ids = self.pipeline.process_articles(articles)
                    logger.info(
                        f"{job_name} job completed: {len(stored_ids)} articles stored"
                    )
                else:
                    logger.warning(f"{job_name} job completed: no articles fetched")

                # Calculate time to next execution
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, interval - elapsed)

                if sleep_time > 0:
                    logger.info(
                        f"{job_name} job sleeping for {sleep_time:.1f}s until next run"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(
                        f"{job_name} job took longer than interval ({elapsed:.1f}s > {interval}s)"
                    )

            except asyncio.CancelledError:
                logger.info(f"{job_name} job cancelled")
                break
            except Exception as e:
                logger.error(f"Error in {job_name} job: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(min(60, interval / 10))

    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        logger.info("Starting news worker scheduler")

        try:
            # Start main fetch job with default interval
            main_interval = self.config.get("newsapi", {}).get(
                "interval", WorkerConfig.DEFAULT_POLL_INTERVAL
            )

            main_task = asyncio.create_task(
                self._run_fetch_job("main_fetch", main_interval)
            )
            self.tasks["main_fetch"] = main_task

            logger.info(f"Scheduler started with {len(self.tasks)} active jobs")

            # Wait for all tasks to complete
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
        finally:
            logger.info("Scheduler stopped")

    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return

        logger.info("Stopping scheduler...")
        self.running = False

        # Cancel all running tasks
        for task_name, task in self.tasks.items():
            if not task.done():
                logger.info(f"Cancelling task: {task_name}")
                task.cancel()

        # Wait for tasks to finish cancelling
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

        self.tasks.clear()
        logger.info("Scheduler stopped")

    async def run_single_fetch(self):
        """Run a single fetch operation (useful for testing)"""
        logger.info("Running single fetch operation")

        try:
            articles = await self.fetcher.fetch_all_sources()
            if articles:
                stored_ids = self.pipeline.process_articles(articles)
                logger.info(
                    f"Single fetch completed: {len(stored_ids)} articles stored"
                )
                return stored_ids
            else:
                logger.warning("Single fetch completed: no articles fetched")
                return []
        except Exception as e:
            logger.error(f"Error in single fetch: {e}")
            return []

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status"""
        return {
            "running": self.running,
            "active_tasks": len(self.tasks),
            "task_names": list(self.tasks.keys()),
            "config": self.config,
            "article_count": self.pipeline.get_article_count(),
            "recent_articles": self.pipeline.get_recent_articles(5),
        }
