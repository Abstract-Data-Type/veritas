
# Load .env file from project root (backend/)
from pathlib import Path

from dotenv import load_dotenv

# Path: main.py -> veritas_news/ -> src/ -> backend/
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, UTC
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api.routes_articles import router as articles_router
from .api.routes_bias_ratings import router as bias_ratings_router
from .db.init_db import init_db
from .worker.news_worker import NewsWorker

# Global worker instance and task
worker_task = None
news_worker = None

# Maintenance mode state
maintenance_state = {
    "is_running": False,
    "started_at": None,
    "last_completed": None,
    "next_refresh": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    global worker_task, news_worker

    # Startup
    logger.info("🚀 Starting Veritas News API...")

    # Initialize database
    success = init_db()
    if success:
        logger.info("✅ Database initialized successfully")
    else:
        logger.error("❌ Database initialization failed")

    # Start background worker if enabled
    worker_enabled = os.getenv("WORKER_ENABLED", "true").lower() == "true"
    if worker_enabled:
        logger.info("🔄 Starting background news worker...")

        # Get worker configuration from environment
        use_newsapi = os.getenv("WORKER_USE_NEWSAPI", "false").lower() == "true"
        use_cnn = os.getenv("WORKER_USE_CNN", "false").lower() == "true"
        hours_back = int(os.getenv("WORKER_HOURS_BACK", "1"))
        limit = int(os.getenv("WORKER_LIMIT", "5"))

        news_worker = NewsWorker(hours_back=hours_back, limit=limit)

        # 12-hour refresh cycle
        refresh_interval = 12 * 60 * 60  # 12 hours in seconds

        async def worker_loop():
            global maintenance_state
            first_run = True
            while news_worker.running:
                try:
                    # Set maintenance mode ON
                    maintenance_state["is_running"] = True
                    maintenance_state["started_at"] = datetime.now(UTC).isoformat()

                    if first_run:
                        logger.info("🚀 Running initial article fetch with summary + LCCM analysis...")
                        first_run = False
                    else:
                        logger.info("🔄 Starting 12-hour refresh cycle...")
                        # NOTE: We no longer wipe the database to preserve article URLs
                        # This ensures links remain stable across refresh cycles

                    count = await news_worker.run_single_fetch(
                        use_cnn=use_cnn, use_newsapi=use_newsapi
                    )
                    logger.info(f"📊 Fetch cycle complete: {count} articles processed with full LLM analysis")

                    # Set maintenance mode OFF
                    maintenance_state["is_running"] = False
                    maintenance_state["last_completed"] = datetime.now(UTC).isoformat()
                    maintenance_state["next_refresh"] = datetime.fromtimestamp(
                        datetime.now(UTC).timestamp() + refresh_interval, UTC
                    ).isoformat()

                    logger.info("⏰ Next refresh in 12 hours")
                    await asyncio.sleep(refresh_interval)
                except asyncio.CancelledError:
                    logger.info("Worker cancelled")
                    maintenance_state["is_running"] = False
                    break
                except Exception as e:
                    logger.error(f"❌ Worker error: {e}")
                    maintenance_state["is_running"] = False
                    await asyncio.sleep(60)

        news_worker.running = True
        worker_task = asyncio.create_task(worker_loop())
        logger.info("✅ Background worker started (12-hour refresh cycle)")
    else:
        logger.info("⏸️  Background worker disabled (set WORKER_ENABLED=true to enable)")

    logger.info("🚀 Application startup complete")

    yield

    # Shutdown
    logger.info("🛑 Shutting down application...")
    if news_worker:
        logger.info("🛑 Stopping background worker...")
        news_worker.stop()
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Background worker stopped")
    logger.info("👋 Application shutdown complete")


app = FastAPI(title="Veritas News API", version="1.0.0", lifespan=lifespan)

# CORS setup (allow frontend during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(bias_ratings_router, prefix="/bias_ratings", tags=["Bias Ratings"])
app.include_router(articles_router, prefix="/articles", tags=["Articles"])


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Veritas News API is running."}


@app.get("/status")
def get_status():
    """Get current system status including maintenance mode"""
    return {
        "status": "ok",
        "maintenance": maintenance_state,
    }


def run():
    """Entry point for the CLI script."""
    import uvicorn
    uvicorn.run("veritas_news.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
