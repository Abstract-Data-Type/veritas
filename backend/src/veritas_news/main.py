
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

        # Determine which fetch method to use
        async def worker_loop():
            while news_worker.running:
                try:
                    await news_worker.run_single_fetch(
                        use_cnn=use_cnn, use_newsapi=use_newsapi
                    )
                    # Wait before next fetch
                    interval = int(os.getenv("WORKER_SCHEDULE_INTERVAL", "1800"))
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    logger.info("Worker cancelled")
                    break
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    await asyncio.sleep(60)

        news_worker.running = True
        worker_task = asyncio.create_task(worker_loop())
        logger.info("✅ Background worker started")
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


def run():
    """Entry point for the CLI script."""
    import uvicorn
    uvicorn.run("veritas_news.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
