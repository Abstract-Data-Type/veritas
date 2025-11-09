from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BiasRatingBase(BaseModel):
    """Base schema for bias rating"""

    bias_score: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Bias score between -1 (left bias) and 1 (right bias)",
    )
    reasoning: Optional[str] = Field(
        None, description="Reasoning behind the bias rating"
    )


class BiasRatingCreate(BiasRatingBase):
    """Schema for creating a new bias rating"""

    article_id: int = Field(..., description="ID of the article being rated")


class BiasRatingUpdate(BiasRatingBase):
    """Schema for updating an existing bias rating"""

    pass


class BiasRatingResponse(BiasRatingBase):
    """Schema for bias rating response"""

    rating_id: int = Field(..., description="Unique identifier for the bias rating")
    article_id: int = Field(..., description="ID of the article being rated")
    evaluated_at: datetime = Field(
        ..., description="Timestamp when the rating was evaluated"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class BiasRatingListResponse(BaseModel):
    """Schema for list of bias ratings response"""

    ratings: list[BiasRatingResponse]
    total: int

    class Config:
        from_attributes = True
