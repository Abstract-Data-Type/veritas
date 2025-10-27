from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
from sqlite3 import Connection

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bias ratings: {str(e)}"
        )
    finally:
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