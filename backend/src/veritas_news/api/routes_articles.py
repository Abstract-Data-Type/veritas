from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db.sqlalchemy import get_session
from ..models.sqlalchemy_models import Article, BiasRating

router = APIRouter()

from fastapi import Header, HTTPException
import os
from ..worker.news_worker import NewsWorker

@router.get("/fetch")
async def trigger_fetch(
    authorization: str | None = Header(default=None),
    use_newsapi: bool = Query(default=False),
    use_cnn: bool = Query(default=False),
    limit: int = Query(default=5),
):
    """
    Trigger a news fetch manually.
    Protected by Authorization header (Bearer CRON_SECRET).
    """
    expected_secret = os.getenv("CRON_SECRET")
    # If CRON_SECRET is not set, deny all requests for security
    if not expected_secret:
        raise HTTPException(status_code=401, detail="CRON_SECRET not configured")
    
    if not authorization or authorization != f"Bearer {expected_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    worker = NewsWorker(limit=limit)
    count = await worker.run_single_fetch(use_cnn=use_cnn, use_newsapi=use_newsapi)
    return {"status": "ok", "fetched": count}



class BiasRatingInfo(BaseModel):
    """Bias rating information for an article"""

    rating_id: int
    bias_score: float | None
    reasoning: str | None
    evaluated_at: datetime
    # SECM scores (new ideological scoring system)
    secm_ideological_score: float | None = None
    secm_epistemic_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(BaseModel):
    """Response model for a single article"""

    article_id: int
    title: str
    source: str | None
    url: str | None
    published_at: datetime | None
    raw_text: str | None
    created_at: datetime
    bias_rating: BiasRatingInfo | None

    model_config = ConfigDict(from_attributes=True)


class ArticleListResponse(BaseModel):
    """Response model for list of articles"""

    articles: list[ArticleResponse]
    total: int


@router.get("/latest", response_model=ArticleListResponse)
async def get_latest_articles(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of articles to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of articles to skip"),
    start_date: datetime | None = Query(
        default=None, description="Filter articles published after this date"
    ),
    end_date: datetime | None = Query(
        default=None, description="Filter articles published before this date"
    ),
    min_bias_score: float | None = Query(
        default=None, ge=-1.0, le=1.0, description="Minimum bias score"
    ),
    max_bias_score: float | None = Query(
        default=None, ge=-1.0, le=1.0, description="Maximum bias score"
    ),
    db: Session = Depends(get_session),
):
    """
    Get the latest articles with their bias ratings.

    This endpoint is used by the UI to display recent articles.
    Articles are returned with their associated bias ratings if available.

    Args:
        limit: Maximum number of articles to return (1-100, default 20)
        offset: Number of articles to skip for pagination (default 0)
        start_date: Filter articles published after this date (optional)
        end_date: Filter articles published before this date (optional)
        min_bias_score: Minimum bias score to include (optional, -1.0 to 1.0)
        max_bias_score: Maximum bias score to include (optional, -1.0 to 1.0)

    Returns:
        List of articles with bias ratings and total count
    """
    # Start building query with left join to bias_ratings
    query = db.query(Article).outerjoin(
        BiasRating, Article.article_id == BiasRating.article_id
    )

    # Apply date filters
    if start_date:
        query = query.filter(Article.published_at >= start_date)

    if end_date:
        query = query.filter(Article.published_at <= end_date)

    if min_bias_score is not None:
        query = query.filter(BiasRating.bias_score >= min_bias_score)

    if max_bias_score is not None:
        query = query.filter(BiasRating.bias_score <= max_bias_score)

    # Get articles with pagination
    articles = (
        query.order_by(Article.created_at.desc()).offset(offset).limit(limit).all()
    )

    # Build response with bias rating info
    article_responses = []
    for article in articles:
        # Get the first (and should be only) bias rating for this article
        bias_rating_info = None
        if article.bias_ratings:
            rating = article.bias_ratings[0]
            bias_rating_info = BiasRatingInfo(
                rating_id=rating.rating_id,
                bias_score=rating.bias_score,
                reasoning=rating.reasoning,
                evaluated_at=rating.evaluated_at,
                secm_ideological_score=rating.secm_ideological_score,
                secm_epistemic_score=rating.secm_epistemic_score,
            )

        article_responses.append(
            ArticleResponse(
                article_id=article.article_id,
                title=article.title,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                raw_text=article.raw_text,
                created_at=article.created_at,
                bias_rating=bias_rating_info,
            )
        )

    return ArticleListResponse(articles=article_responses, total=len(article_responses))
