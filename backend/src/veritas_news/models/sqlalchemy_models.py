from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.sqlalchemy import Base


class User(Base):
    """User model representing application users."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        "user_id", Integer, primary_key=True, index=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        "username", String, unique=True, nullable=False
    )
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    interactions: Mapped[list[UserInteraction]] = relationship(
        "UserInteraction", back_populates="user"
    )


class Article(Base):
    """Article model representing news articles."""

    __tablename__ = "articles"

    article_id: Mapped[int] = mapped_column(
        "article_id", Integer, primary_key=True, index=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    summaries: Mapped[list[Summary]] = relationship(
        "Summary", back_populates="article"
    )
    bias_ratings: Mapped[list[BiasRating]] = relationship(
        "BiasRating", back_populates="article"
    )
    interactions: Mapped[list[UserInteraction]] = relationship(
        "UserInteraction", back_populates="article"
    )


class Summary(Base):
    """Summary model for article summaries."""

    __tablename__ = "summaries"

    summary_id: Mapped[int] = mapped_column(
        "summary_id", Integer, primary_key=True, index=True, autoincrement=True
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.article_id"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    article: Mapped[Article] = relationship("Article", back_populates="summaries")


class BiasRating(Base):
    """Bias rating model for article political bias analysis."""

    __tablename__ = "bias_ratings"

    rating_id: Mapped[int] = mapped_column(
        "rating_id", Integer, primary_key=True, index=True, autoincrement=True
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.article_id"), nullable=False
    )
    bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Multi-dimensional bias scores
    partisan_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    affective_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    framing_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    sourcing_bias: Mapped[float | None] = mapped_column(Float, nullable=True)

    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    article: Mapped[Article] = relationship("Article", back_populates="bias_ratings")


class UserInteraction(Base):
    """User interaction model for tracking user activity with articles."""

    __tablename__ = "user_interactions"

    __table_args__ = (
        CheckConstraint(
            "action IN ('viewed', 'liked', 'bookmarked')", name="check_action"
        ),
    )

    interaction_id: Mapped[int] = mapped_column(
        "interaction_id", Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.article_id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    interacted_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="interactions")
    article: Mapped[Article] = relationship("Article", back_populates="interactions")
