from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.sqlalchemy import get_session
from ..models.sqlalchemy_models import Article, BiasRating

router = APIRouter()


class BiasRatingInfo(BaseModel):
    """Bias rating information for an article"""

    rating_id: int
    bias_score: Optional[float]
    reasoning: Optional[str]
    evaluated_at: datetime

    class Config:
        from_attributes = True


class ArticleResponse(BaseModel):
    """Response model for a single article"""

    article_id: int
    title: str
    source: Optional[str]
    url: Optional[str]
    published_at: Optional[datetime]
    raw_text: Optional[str]
    created_at: datetime
    bias_rating: Optional[BiasRatingInfo]

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Response model for list of articles"""

    articles: List[ArticleResponse]
    total: int


@router.get("/latest", response_model=ArticleListResponse)
async def get_latest_articles(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of articles to return"
    ),
    db: Session = Depends(get_session),
):
    """
    Get the latest articles with their bias ratings.

    This endpoint is used by the UI to display recent articles.
    Articles are returned with their associated bias ratings if available.

    Args:
        limit: Maximum number of articles to return (1-100, default 20)

    Returns:
        List of articles with bias ratings and total count
    """
    # Query articles with left join to bias_ratings
    articles = (
        db.query(Article)
        .outerjoin(BiasRating, Article.article_id == BiasRating.article_id)
        .order_by(Article.created_at.desc())
        .limit(limit)
        .all()
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
