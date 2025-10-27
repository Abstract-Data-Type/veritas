from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
from sqlite3 import Connection
import httpx
import os
from loguru import logger
from pydantic import BaseModel

from ..db.init_db import get_connection
from ..db.bias_rating_db import (
    get_all_bias_ratings,
    get_bias_rating_by_id,
    update_bias_rating,
    bias_rating_exists
)
from ..models.bias_rating import (
    BiasRatingResponse,
    BiasRatingListResponse,
    BiasRatingUpdate
)

router = APIRouter()


def get_db_connection() -> Connection:
    """Dependency to get database connection"""
    return get_connection()


@router.get("/", response_model=BiasRatingListResponse)
async def get_bias_ratings(conn: Connection = Depends(get_db_connection)):
    """
    Retrieve all bias ratings
    
    Returns:
        List of all bias ratings in the database
    """
    try:
        ratings_data = get_all_bias_ratings(conn)
        
        # Convert to Pydantic models
        ratings = [BiasRatingResponse(**rating) for rating in ratings_data]
        
        return BiasRatingListResponse(
            ratings=ratings,
            total=len(ratings)
        )
    
    except Exception as e:
        conn.close()  # Close connection on error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bias ratings: {str(e)}"
        )
    
    # Close connection on successful completion
    conn.close()


@router.get("/{rating_id}", response_model=BiasRatingResponse)
async def get_bias_rating(rating_id: int, conn: Connection = Depends(get_db_connection)):
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
        rating_data = get_bias_rating_by_id(conn, rating_id)
        
        if not rating_data:
            raise HTTPException(
                status_code=404,
                detail=f"Bias rating with ID {rating_id} not found"
            )
        
        return BiasRatingResponse(**rating_data)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bias rating: {str(e)}"
        )
    finally:
        conn.close()


@router.put("/{rating_id}", response_model=BiasRatingResponse)
async def update_bias_rating_endpoint(
    rating_id: int, 
    rating_update: BiasRatingUpdate,
    conn: Connection = Depends(get_db_connection)
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
        # Check if the rating exists
        if not bias_rating_exists(conn, rating_id):
            raise HTTPException(
                status_code=404,
                detail=f"Bias rating with ID {rating_id} not found"
            )
        
        # Validate bias_score range if provided
        if rating_update.bias_score is not None:
            if rating_update.bias_score < -1.0 or rating_update.bias_score > 1.0:
                raise HTTPException(
                    status_code=422,
                    detail="Bias score must be between -1.0 and 1.0"
                )
        
        # Update the rating
        success = update_bias_rating(
            conn,
            rating_id,
            bias_score=rating_update.bias_score,
            reasoning=rating_update.reasoning
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update bias rating"
            )
        
        # Return the updated rating
        updated_rating = get_bias_rating_by_id(conn, rating_id)
        return BiasRatingResponse(**updated_rating)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update bias rating: {str(e)}"
        )
    finally:
        conn.close()


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
        raise HTTPException(
            status_code=400,
            detail="article_text cannot be empty"
        )
    
    summarization_service_url = os.environ.get(
        "SUMMARIZATION_SERVICE_URL",
        "http://localhost:8000"
    )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{summarization_service_url}/summarize",
                json={"article_text": request.article_text}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"summary": data.get("summary", "")}
            elif response.status_code >= 500:
                logger.error(f"Summarization service error: {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="Summary generation failed"
                )
            else:
                logger.warning(f"Unexpected response from summarization service: {response.status_code}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate summary"
                )
    
    except httpx.TimeoutException:
        logger.error("Summarization service timeout")
        raise HTTPException(
            status_code=504,
            detail="Summarization service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Summarization service connection error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Cannot reach summarization service"
        )
    except Exception as e:
        logger.error(f"Unexpected error in summarize endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )