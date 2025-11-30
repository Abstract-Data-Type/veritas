"""Utility functions for working with BiasRating models."""


from .sqlalchemy_models import BiasRating


def normalize_score_to_range(score: float, from_min: float = 1.0, from_max: float = 7.0,
                              to_min: float = -1.0, to_max: float = 1.0) -> float:
    """
    Normalize a score from one range to another.

    Default: converts 1-7 scale to -1 to 1 scale.
    - 1 → -1 (far left / minimal bias)
    - 4 → 0 (center / neutral)
    - 7 → +1 (far right / maximal bias)

    Args:
        score: The score to normalize
        from_min: Minimum of original range (default 1.0)
        from_max: Maximum of original range (default 7.0)
        to_min: Minimum of target range (default -1.0)
        to_max: Maximum of target range (default 1.0)

    Returns:
        Normalized score in target range
    """
    # Linear interpolation: (score - from_min) / (from_max - from_min) * (to_max - to_min) + to_min
    normalized = (score - from_min) / (from_max - from_min) * (to_max - to_min) + to_min
    return normalized


def get_overall_bias_score(bias_rating: BiasRating) -> float | None:
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


def get_all_dimension_scores(bias_rating: BiasRating) -> dict[str, float | None]:
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


def get_dimension_score(bias_rating: BiasRating, dimension: str) -> float | None:
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
