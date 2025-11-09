import os
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.sqlalchemy import get_session
from ..models.bias_rating import (
    BiasRatingListResponse,
    BiasRatingResponse,
    BiasRatingUpdate,
)
from ..models.sqlalchemy_models import BiasRating

router = APIRouter()


@router.get("/", response_model=BiasRatingListResponse)
async def get_bias_ratings(db: Session = Depends(get_session)):
    """
    Retrieve all bias ratings

    Returns:
        List of all bias ratings in the database
    """
    try:
        records = db.query(BiasRating).order_by(BiasRating.evaluated_at.desc()).all()
        ratings = [
            BiasRatingResponse(
                rating_id=r.rating_id,
                article_id=r.article_id,
                bias_score=r.bias_score,
                reasoning=r.reasoning,
                evaluated_at=r.evaluated_at,
            )
            for r in records
        ]
        return BiasRatingListResponse(ratings=ratings, total=len(ratings))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bias ratings: {str(e)}"
        )


@router.get("/{rating_id}", response_model=BiasRatingResponse)
async def get_bias_rating(rating_id: int, db: Session = Depends(get_session)):
    """
    Retrieve a single bias rating by ID

    Args:
        rating_id: The ID of the bias rating to retrieve

    Returns:
        The bias rating with the specified ID

    Raises:
        HTTPException: If the bias rating is not found
    """
    try:
        r = db.query(BiasRating).filter(BiasRating.rating_id == rating_id).first()
        if not r:
            raise HTTPException(
                status_code=404, detail=f"Bias rating with ID {rating_id} not found"
            )
        return BiasRatingResponse(
            rating_id=r.rating_id,
            article_id=r.article_id,
            bias_score=r.bias_score,
            reasoning=r.reasoning,
            evaluated_at=r.evaluated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bias rating: {str(e)}"
        )


@router.put("/{rating_id}", response_model=BiasRatingResponse)
async def update_bias_rating_endpoint(
    rating_id: int, rating_update: BiasRatingUpdate, db: Session = Depends(get_session)
):
    """
    Update an existing bias rating

    Args:
        rating_id: The ID of the bias rating to update
        rating_update: The updated bias rating data

    Returns:
        The updated bias rating

    Raises:
        HTTPException: If the bias rating is not found or update fails
    """
    try:
        r = db.query(BiasRating).filter(BiasRating.rating_id == rating_id).first()
        if not r:
            raise HTTPException(
                status_code=404, detail=f"Bias rating with ID {rating_id} not found"
            )

        if rating_update.bias_score is not None:
            if rating_update.bias_score < -1.0 or rating_update.bias_score > 1.0:
                raise HTTPException(
                    status_code=422, detail="Bias score must be between -1.0 and 1.0"
                )

        if rating_update.bias_score is not None:
            r.bias_score = rating_update.bias_score
        if rating_update.reasoning is not None:
            r.reasoning = rating_update.reasoning

        from datetime import datetime

        r.evaluated_at = datetime.utcnow()
        db.add(r)
        db.commit()
        db.refresh(r)
        return BiasRatingResponse(
            rating_id=r.rating_id,
            article_id=r.article_id,
            bias_score=r.bias_score,
            reasoning=r.reasoning,
            evaluated_at=r.evaluated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update bias rating: {str(e)}"
        )


class SummarizeRequest(BaseModel):
    article_text: str


@router.post("/summarize")
async def summarize_article(request: SummarizeRequest):
    """
    Summarize an article using the external summarization service.

    Args:
        request: Contains article_text to summarize

    Returns:
        JSON with summary field containing the generated summary
    """
    if not request.article_text or not request.article_text.strip():
        return JSONResponse(
            status_code=422, content={"detail": "article_text cannot be empty"}
        )

    summarization_service_url = os.environ.get(
        "SUMMARIZATION_SERVICE_URL", "http://localhost:8000"
    ).rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{summarization_service_url}/summarize",
                json={"article_text": request.article_text},
            )

            if response.status_code == 200:
                # Malformed JSON from upstream should surface as 502
                try:
                    data = response.json()
                except Exception:
                    logger.error("Summarization service returned invalid JSON")
                    return JSONResponse(
                        status_code=502,
                        content={
                            "detail": "Summarization service returned invalid JSON"
                        },
                    )

                # Ensure JSON has expected shape
                if not isinstance(data, dict) or "summary" not in data:
                    logger.error(f"Summarization service missing 'summary' key: {data}")
                    return JSONResponse(
                        status_code=502,
                        content={
                            "detail": "Summarization service returned empty summary"
                        },
                    )

                raw_summary = data.get("summary")
                # Coerce to string in case upstream returns non-string
                summary = str(raw_summary).strip() if raw_summary is not None else ""

                # Validate that summary is not empty
                if not summary:
                    logger.error(
                        f"Summarization service returned empty summary: {data}"
                    )
                    return JSONResponse(
                        status_code=502,
                        content={
                            "detail": "Summarization service returned empty summary"
                        },
                    )

                return {"summary": summary}
            elif response.status_code >= 500:
                logger.error(f"Summarization service error: {response.text}")
                return JSONResponse(
                    status_code=502, content={"detail": "Summary generation failed"}
                )
            elif response.status_code >= 400:
                # Forward client errors (4xx) with appropriate status
                logger.warning(
                    f"Client error from summarization service: {response.status_code} - {response.text}"
                )
                # Forward exact 422 when present, otherwise 400
                forward_code = 422 if response.status_code == 422 else 400
                return JSONResponse(
                    status_code=forward_code,
                    content={
                        "detail": f"Invalid request to summarization service: {response.text}"
                    },
                )
            else:
                # Unexpected status codes (e.g., 3xx redirects)
                logger.error(
                    f"Unexpected status code from summarization service: {response.status_code}"
                )
                return JSONResponse(
                    status_code=502,
                    content={
                        "detail": "Unexpected response from summarization service"
                    },
                )

    except httpx.TimeoutException:
        logger.error("Summarization service timeout")
        return JSONResponse(
            status_code=504, content={"detail": "Summarization service timeout"}
        )
    except httpx.RequestError as e:
        logger.error(f"Summarization service connection error: {e}")
        return JSONResponse(
            status_code=502, content={"detail": "Cannot reach summarization service"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in summarize endpoint: {e}")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )
