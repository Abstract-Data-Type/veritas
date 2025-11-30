"""Scoring functions for bias analysis."""



def score_bias(raw_scores: dict[str, float]) -> dict[str, float]:
    """
    Pluggable scoring function that processes raw LLM scores.

    Initial implementation: simple pass-through (returns scores as-is).
    This function can be extended to implement weighted formulas, normalization, etc.

    Args:
        raw_scores: Dictionary mapping dimension names to raw scores

    Returns:
        Dictionary mapping dimension names to final scores
    """
    # Simple pass-through implementation
    return raw_scores.copy()

