from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# Use the unified SQLite file by default; can be overridden via environment variables
DB_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL",
    f"sqlite:///{os.getenv('DB_PATH', 'veritas_news.db')}"
)

engine = create_engine(
    DB_URL, 
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    echo=False  # Set to True for SQL query logging during development
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_session() -> Generator[Session, None, None]:
    """
    Dependency function to get a database session for FastAPI endpoints.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    """
    Initialize the database by creating all tables defined in SQLAlchemy models.
    This should be called on application startup.
    """
    # Import all models to ensure they're registered with Base.metadata
    from ..models.sqlalchemy_models import (
        User,
        Article,
        Summary,
        BiasRating,
        UserInteraction
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)
