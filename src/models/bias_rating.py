"""Utility functions for working with BiasRating models."""

from typing import Dict, Optional

from .sqlalchemy_models import BiasRating


def get_overall_bias_score(bias_rating: BiasRating) -> Optional[float]:
    """
    Compute average of 4 dimensions as overall bias score.
    
    Args:
        bias_rating: BiasRating instance
        
    Returns:
        Average of non-null dimension scores, or None if all are null
    """
    scores = [
        bias_rating.partisan_bias,
        bias_rating.affective_bias,
        bias_rating.framing_bias,
        bias_rating.sourcing_bias,
    ]
    
    # Filter out None values
    valid_scores = [s for s in scores if s is not None]
    
    if not valid_scores:
        return None
    
    return sum(valid_scores) / len(valid_scores)


def get_all_dimension_scores(bias_rating: BiasRating) -> Dict[str, Optional[float]]:
    """
    Return dictionary of all 4 dimension scores.
    
    Args:
        bias_rating: BiasRating instance
        
    Returns:
        Dictionary mapping dimension names to scores
    """
    return {
        "partisan_bias": bias_rating.partisan_bias,
        "affective_bias": bias_rating.affective_bias,
        "framing_bias": bias_rating.framing_bias,
        "sourcing_bias": bias_rating.sourcing_bias,
    }


def get_dimension_score(bias_rating: BiasRating, dimension: str) -> Optional[float]:
    """
    Get individual dimension score by name.
    
    Args:
        bias_rating: BiasRating instance
        dimension: Dimension name (partisan_bias, affective_bias, framing_bias, sourcing_bias)
        
    Returns:
        Score for the specified dimension
        
    Raises:
        ValueError: If dimension name is invalid
    """
    valid_dimensions = ["partisan_bias", "affective_bias", "framing_bias", "sourcing_bias"]
    
    if dimension not in valid_dimensions:
        raise ValueError(
            f"Invalid dimension '{dimension}'. Must be one of: {', '.join(valid_dimensions)}"
        )
    
    return getattr(bias_rating, dimension)
