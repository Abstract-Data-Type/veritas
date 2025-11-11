from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai import rate_bias, summarize_with_gemini
from ..db.sqlalchemy import get_session
from ..models.sqlalchemy_models import Article, BiasRating

router = APIRouter()


class SummarizeRequest(BaseModel):
    """Request to summarize article text"""

    article_text: str


class AnalyzeArticleRequest(BaseModel):
    """Request to analyze an article for bias"""

    article_id: int


class AnalyzeArticleResponse(BaseModel):
    """Response after analyzing article for bias"""

    rating_id: int
    article_id: int
    bias_score: float
    reasoning: str
    scores: Dict[str, float]


@router.post("/analyze", response_model=AnalyzeArticleResponse)
async def analyze_article_bias(
    request: AnalyzeArticleRequest, db: Session = Depends(get_session)
):
    """
    Analyze an article for political bias using the AI library.

    This endpoint is called by the worker after storing a new article.
    It fetches the article text, calls the bias rating function, and stores the results.

    Args:
        request: Contains article_id to analyze

    Returns:
        The created bias rating with scores

    Raises:
        HTTPException: If article not found or bias analysis fails
    """
    # Fetch the article
    article = db.query(Article).filter(Article.article_id == request.article_id).first()
    if not article:
        raise HTTPException(
            status_code=404, detail=f"Article {request.article_id} not found"
        )

    if not article.raw_text or not article.raw_text.strip():
        raise HTTPException(
            status_code=422, detail="Article has no text content to analyze"
        )

    # Check if bias rating already exists
    existing_rating = (
        db.query(BiasRating).filter(BiasRating.article_id == request.article_id).first()
    )
    if existing_rating:
        logger.info(
            f"Bias rating already exists for article {request.article_id}, returning existing"
        )
        return AnalyzeArticleResponse(
            rating_id=existing_rating.rating_id,
            article_id=existing_rating.article_id,
            bias_score=existing_rating.bias_score or 0.0,
            reasoning=existing_rating.reasoning or "",
            scores={},
        )

    # Call the bias rating function directly
    try:
        logger.info(f"Calling bias analysis for article {request.article_id}")
        bias_result = await rate_bias(article.raw_text)

        # Extract scores from result
        scores = bias_result.get("scores", {})
        # For now, we don't have a single bias_score, so we'll use None or calculate one
        # The database schema expects bias_score, but we're storing scores dict
        bias_score = None  # Could calculate from scores if needed

        # Store the bias rating
        new_rating = BiasRating(
            article_id=request.article_id,
            bias_score=bias_score,
            reasoning=None,  # Could add reasoning extraction later
            evaluated_at=datetime.utcnow(),
        )

        db.add(new_rating)
        db.commit()
        db.refresh(new_rating)

        logger.info(
            f"Stored bias rating {new_rating.rating_id} for article {request.article_id}"
        )

        return AnalyzeArticleResponse(
            rating_id=new_rating.rating_id,
            article_id=new_rating.article_id,
            bias_score=new_rating.bias_score or 0.0,
            reasoning=new_rating.reasoning or "",
            scores=scores,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 502 from rate_bias)
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing bias: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze article bias: {str(e)}"
        )


@router.post("/summarize")
async def summarize_article(request: SummarizeRequest):
    """
    Summarize article text using the AI library.

    This endpoint validates the input and calls the summarization function directly.

    Args:
        request: Contains article_text to summarize

    Returns:
        Dictionary with 'summary' key containing the summarized text

    Raises:
        HTTPException: 422 for invalid input, 500/502 for errors
    """
    # Validate article text
    if not request.article_text or not request.article_text.strip():
        raise HTTPException(
            status_code=422, detail="Article text is required and cannot be empty"
        )

    try:
        logger.info("Calling summarization function")
        summary = summarize_with_gemini(request.article_text)

        if not summary or not summary.strip():
            logger.error("Summarization function returned empty summary")
            raise HTTPException(
                status_code=502, detail="Summarization returned empty summary"
            )

        return {"summary": summary}

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 500/502 from summarize_with_gemini)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to summarize article: {str(e)}"
        )
