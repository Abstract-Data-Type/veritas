from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.init_db import get_connection, init_db
from loguru import logger

app = FastAPI(title="Veritas News API", version="1.0.0")

# CORS setup (allow frontend during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Startup event ----
@app.on_event("startup")
def startup_event():
    """Initialize database and log startup status."""
    conn = get_connection()
    init_db(conn)
    logger.info("✅ Database initialized successfully.")
    logger.info("🚀 Application startup complete.")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Veritas News API is running."}
