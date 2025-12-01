"""Utility functions for working with BiasRating models."""

import json

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


def get_secm_scores(bias_rating: BiasRating) -> dict[str, float | None]:
    """
    Return SECM ideological and epistemic scores.
    
    Args:
        bias_rating: BiasRating instance
        
    Returns:
        Dictionary with 'ideological_score' and 'epistemic_score'
    """
    return {
        "ideological_score": bias_rating.secm_ideological_score,
        "epistemic_score": bias_rating.secm_epistemic_score,
    }


def get_secm_variables(bias_rating: BiasRating) -> dict[str, int | None]:
    """
    Return all 22 SECM binary variable values.
    
    Args:
        bias_rating: BiasRating instance
        
    Returns:
        Dictionary mapping variable names to binary values (0/1) or None
    """
    return {
        # Ideological Left Markers
        "secm_ideol_l1_systemic_naming": bias_rating.secm_ideol_l1_systemic_naming,
        "secm_ideol_l2_power_gap_lexicon": bias_rating.secm_ideol_l2_power_gap_lexicon,
        "secm_ideol_l3_elite_culpability": bias_rating.secm_ideol_l3_elite_culpability,
        "secm_ideol_l4_resource_redistribution": bias_rating.secm_ideol_l4_resource_redistribution,
        "secm_ideol_l5_change_as_justice": bias_rating.secm_ideol_l5_change_as_justice,
        "secm_ideol_l6_care_harm": bias_rating.secm_ideol_l6_care_harm,
        # Ideological Right Markers
        "secm_ideol_r1_agentic_culpability": bias_rating.secm_ideol_r1_agentic_culpability,
        "secm_ideol_r2_order_lexicon": bias_rating.secm_ideol_r2_order_lexicon,
        "secm_ideol_r3_institutional_defense": bias_rating.secm_ideol_r3_institutional_defense,
        "secm_ideol_r4_meritocratic_defense": bias_rating.secm_ideol_r4_meritocratic_defense,
        "secm_ideol_r5_change_as_threat": bias_rating.secm_ideol_r5_change_as_threat,
        "secm_ideol_r6_sanctity_degradation": bias_rating.secm_ideol_r6_sanctity_degradation,
        # Epistemic High Integrity Markers
        "secm_epist_h1_primary_documentation": bias_rating.secm_epist_h1_primary_documentation,
        "secm_epist_h2_adversarial_sourcing": bias_rating.secm_epist_h2_adversarial_sourcing,
        "secm_epist_h3_specific_attribution": bias_rating.secm_epist_h3_specific_attribution,
        "secm_epist_h4_data_contextualization": bias_rating.secm_epist_h4_data_contextualization,
        "secm_epist_h5_methodological_transparency": bias_rating.secm_epist_h5_methodological_transparency,
        # Epistemic Low Integrity Markers
        "secm_epist_e1_emotive_adjectives": bias_rating.secm_epist_e1_emotive_adjectives,
        "secm_epist_e2_labeling_othering": bias_rating.secm_epist_e2_labeling_othering,
        "secm_epist_e3_causal_certainty": bias_rating.secm_epist_e3_causal_certainty,
        "secm_epist_e4_imperative_direct_address": bias_rating.secm_epist_e4_imperative_direct_address,
        "secm_epist_e5_motivated_reasoning": bias_rating.secm_epist_e5_motivated_reasoning,
    }


def get_secm_reasoning(bias_rating: BiasRating) -> dict[str, str]:
    """
    Parse and return SECM reasoning JSON.
    
    Args:
        bias_rating: BiasRating instance
        
    Returns:
        Dictionary mapping variable names to reasoning strings
        Returns empty dict if reasoning_json is None or invalid
    """
    if not bias_rating.secm_reasoning_json:
        return {}
    
    try:
        return json.loads(bias_rating.secm_reasoning_json)
    except (json.JSONDecodeError, TypeError):
        return {}
