import os
from datetime import datetime
from typing import Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
    Analyze an article for political bias using the LLM service.

    This endpoint is called by the worker after storing a new article.
    It fetches the article text, calls the bias rating service, and stores the results.

    Args:
        request: Contains article_id to analyze

    Returns:
        The created bias rating with scores

    Raises:
        HTTPException: If article not found or bias service fails
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

    # Call the bias rating service
    summarization_service_url = os.environ.get(
        "SUMMARIZATION_SERVICE_URL", "http://localhost:8000"
    ).rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"Calling bias service for article {request.article_id}")
            response = await client.post(
                f"{summarization_service_url}/rate-bias",
                json={"article_text": article.raw_text},
            )

            if response.status_code != 200:
                logger.error(
                    f"Bias service error {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Bias rating service failed: {response.status_code}",
                )

            bias_data = response.json()

            # Extract whatever the bias service returns
            bias_score = bias_data.get("bias_score")
            reasoning = bias_data.get("reasoning", "")
            scores = bias_data.get("scores", {})

            # Store the bias rating with whatever the service provided
            new_rating = BiasRating(
                article_id=request.article_id,
                bias_score=bias_score,
                reasoning=reasoning,
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
                bias_score=new_rating.bias_score,
                reasoning=new_rating.reasoning,
                scores=scores,
            )

    except httpx.TimeoutException:
        logger.error("Bias service timeout")
        raise HTTPException(status_code=504, detail="Bias rating service timeout")
    except httpx.RequestError as e:
        logger.error(f"Bias service connection error: {e}")
        raise HTTPException(status_code=502, detail="Cannot reach bias rating service")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing bias: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze article bias: {str(e)}"
        )


@router.post("/summarize")
async def summarize_article(request: SummarizeRequest):
    """
    Summarize article text using the summarization service.

    This endpoint validates the input and forwards the request to the
    summarization service, handling errors appropriately.

    Args:
        request: Contains article_text to summarize

    Returns:
        Dictionary with 'summary' key containing the summarized text

    Raises:
        HTTPException: 422 for invalid input, 502 for service errors
    """
    # Validate article text
    if not request.article_text or not request.article_text.strip():
        raise HTTPException(
            status_code=422, detail="Article text is required and cannot be empty"
        )

    # Get summarization service URL
    summarization_service_url = os.environ.get(
        "SUMMARIZATION_SERVICE_URL", "http://localhost:8000"
    ).rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("Calling summarization service")
            response = await client.post(
                f"{summarization_service_url}/summarize",
                json={"article_text": request.article_text},
            )

            # Handle 4xx client errors from summarization service
            if 400 <= response.status_code < 500:
                logger.error(
                    f"Summarization service client error {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Invalid request to summarization service: {response.text}",
                )

            # Handle 5xx server errors from summarization service
            if response.status_code >= 500:
                logger.error(
                    f"Summarization service server error {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Summarization service error: {response.status_code}",
                )

            # Handle successful response
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise HTTPException(
                        status_code=502,
                        detail="Summarization service returned invalid JSON",
                    )

                # Check if summary field exists and is not empty
                summary = data.get("summary", "")
                if not summary or not summary.strip():
                    logger.error("Summarization service returned empty summary")
                    raise HTTPException(
                        status_code=502,
                        detail="Summarization service returned empty summary",
                    )

                return {"summary": summary}

            # Unexpected status code
            logger.error(f"Unexpected status code {response.status_code}")
            raise HTTPException(
                status_code=502,
                detail=f"Unexpected response from summarization service: {response.status_code}",
            )

    except httpx.TimeoutException:
        logger.error("Summarization service timeout")
        raise HTTPException(status_code=504, detail="Summarization service timeout")
    except httpx.RequestError as e:
        logger.error(f"Summarization service connection error: {e}")
        raise HTTPException(
            status_code=502, detail="Cannot reach summarization service"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to summarize article: {str(e)}"
        )
