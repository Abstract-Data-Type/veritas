from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api.routes_articles import router as articles_router
from .api.routes_bias_ratings import router as bias_ratings_router
from .db.init_db import init_db

app = FastAPI(title="Veritas News API", version="1.0.0")

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


# ---- Startup event ----
@app.on_event("startup")
def startup_event():
    """Initialize database and log startup status."""
    # Initialize all SQLAlchemy tables
    success = init_db()
    if success:
        logger.info("✅ Database initialized successfully.")
    else:
        logger.error("❌ Database initialization failed.")
    logger.info("🚀 Application startup complete.")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Veritas News API is running."}
