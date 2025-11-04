from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..db.sqlalchemy import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bias_ratings: Mapped[list["BiasRating"]] = relationship("BiasRating", back_populates="user")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_published: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    summaries: Mapped[list["Summary"]] = relationship("Summary", back_populates="article")
    bias_ratings: Mapped[list["BiasRating"]] = relationship("BiasRating", back_populates="article")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    bias_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    article: Mapped[Article] = relationship("Article", back_populates="summaries")


class BiasRating(Base):
    __tablename__ = "bias_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    article: Mapped[Article] = relationship("Article", back_populates="bias_ratings")
    user: Mapped[User] = relationship("User", back_populates="bias_ratings")
