from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# Use a separate default DB file for SQLAlchemy to avoid conflicting with existing sqlite3 schema
DB_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL",
    f"sqlite:///{os.getenv('SQLALCHEMY_DB_PATH', 'veritas_news_sa.db')}"
)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    # Import models so they are registered with Base before create_all
    from ..models.sqlalchemy_models import User, Article, Summary, BiasRating  # noqa: F401

    Base.metadata.create_all(bind=engine)
