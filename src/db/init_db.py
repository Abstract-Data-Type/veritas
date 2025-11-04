"""
Database initialization module using SQLAlchemy.
This replaces the old sqlite3-based init_db implementation.
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from .sqlalchemy import SessionLocal, engine, Base, get_session
from loguru import logger


@contextmanager
def get_connection() -> Generator[Session, None, None]:
    """
    Get a SQLAlchemy database session (replaces old sqlite3 connection).
    
    This function maintains backwards compatibility with the old get_connection()
    interface, but now returns a SQLAlchemy Session instead of a sqlite3 Connection.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(db: Session = None) -> bool:
    """
    Initialize the database with required tables using SQLAlchemy.
    
    Args:
        db: Optional SQLAlchemy session (for backwards compatibility, but not used)
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Import all models to ensure they're registered with Base.metadata
        from ..models.sqlalchemy_models import (
            User,
            Article, 
            Summary,
            BiasRating
        )
        
        # Create all tables defined in the models
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
