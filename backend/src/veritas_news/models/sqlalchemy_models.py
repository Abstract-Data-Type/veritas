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

    # Multi-dimensional bias scores (legacy 4-dimension system)
    partisan_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    affective_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    framing_bias: Mapped[float | None] = mapped_column(Float, nullable=True)
    sourcing_bias: Mapped[float | None] = mapped_column(Float, nullable=True)

    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # SECM Binary Variables - Ideological Dimension (Left Markers)
    secm_ideol_l1_systemic_naming: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_l2_power_gap_lexicon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_l3_elite_culpability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_l4_resource_redistribution: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_l5_change_as_justice: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_l6_care_harm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # SECM Binary Variables - Ideological Dimension (Right Markers)
    secm_ideol_r1_agentic_culpability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_r2_order_lexicon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_r3_institutional_defense: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_r4_meritocratic_defense: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_r5_change_as_threat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_ideol_r6_sanctity_degradation: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # SECM Binary Variables - Epistemic Dimension (High Integrity Markers)
    secm_epist_h1_primary_documentation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_h2_adversarial_sourcing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_h3_specific_attribution: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_h4_data_contextualization: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_h5_methodological_transparency: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # SECM Binary Variables - Epistemic Dimension (Low Integrity / Erosion Markers)
    secm_epist_e1_emotive_adjectives: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_e2_labeling_othering: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_e3_causal_certainty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_e4_imperative_direct_address: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secm_epist_e5_motivated_reasoning: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # SECM Final Computed Scores
    secm_ideological_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    secm_epistemic_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # SECM Reasoning Storage (JSON)
    secm_reasoning_json: Mapped[str | None] = mapped_column(Text, nullable=True)

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
