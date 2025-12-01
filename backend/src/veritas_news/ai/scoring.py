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


def score_secm(
    variable_values: dict[str, int],
    k: float = 4.0
) -> dict[str, float]:
    """
    Compute SECM intensity-weighted scores using Bayesian smoothing.
    
    Uses the formulas:
    - Ideological Score (X-axis): (R - L) / (R + L + K)
    - Epistemic Score (Y-axis): (H - E) / (H + E + K)
    
    Where:
    - L = Sum of left markers (secm_ideol_l1 through secm_ideol_l6)
    - R = Sum of right markers (secm_ideol_r1 through secm_ideol_r6)
    - H = Sum of high integrity markers (secm_epist_h1 through secm_epist_h5)
    - E = Sum of low integrity markers (secm_epist_e1 through secm_epist_e5)
    - K = Damping constant for Bayesian smoothing (default: 4.0)
    
    The K constant ensures scores require multiple markers to reach extremes:
    - Single marker (R=1, L=0): score = 1/(1+4) = 0.20 (slight lean)
    - Strong signal (R=8, L=0): score = 8/(8+4) = 0.67 (strong bias)
    
    Args:
        variable_values: Dictionary mapping variable names to binary values (0/1)
        k: Damping constant for intensity weighting (default: 4.0)
    
    Returns:
        Dictionary with:
        - ideological_score: float (~-0.75 to ~+0.75 in practice)
        - epistemic_score: float (~-0.75 to ~+0.75 in practice)
    
    Interpretation:
        0.0 to ±0.15: Neutral/Centrist
        ±0.15 to ±0.35: Leaning
        ±0.35 to ±0.60: Strong Bias
        > ±0.60: Extreme/Radical
    """
    # Sum left markers (L)
    left_vars = [
        "secm_ideol_l1_systemic_naming",
        "secm_ideol_l2_power_gap_lexicon",
        "secm_ideol_l3_elite_culpability",
        "secm_ideol_l4_resource_redistribution",
        "secm_ideol_l5_change_as_justice",
        "secm_ideol_l6_care_harm",
    ]
    L = sum(variable_values.get(var, 0) for var in left_vars)
    
    # Sum right markers (R)
    right_vars = [
        "secm_ideol_r1_agentic_culpability",
        "secm_ideol_r2_order_lexicon",
        "secm_ideol_r3_institutional_defense",
        "secm_ideol_r4_meritocratic_defense",
        "secm_ideol_r5_change_as_threat",
        "secm_ideol_r6_sanctity_degradation",
    ]
    R = sum(variable_values.get(var, 0) for var in right_vars)
    
    # Sum high integrity markers (H)
    high_vars = [
        "secm_epist_h1_primary_documentation",
        "secm_epist_h2_adversarial_sourcing",
        "secm_epist_h3_specific_attribution",
        "secm_epist_h4_data_contextualization",
        "secm_epist_h5_methodological_transparency",
    ]
    H = sum(variable_values.get(var, 0) for var in high_vars)
    
    # Sum low integrity markers (E)
    low_vars = [
        "secm_epist_e1_emotive_adjectives",
        "secm_epist_e2_labeling_othering",
        "secm_epist_e3_causal_certainty",
        "secm_epist_e4_imperative_direct_address",
        "secm_epist_e5_motivated_reasoning",
    ]
    E = sum(variable_values.get(var, 0) for var in low_vars)
    
    # Compute ideological score: (R - L) / (R + L + K)
    ideological_score = (R - L) / (R + L + k)
    
    # Compute epistemic score: (H - E) / (H + E + K)
    epistemic_score = (H - E) / (H + E + k)
    
    return {
        "ideological_score": ideological_score,
        "epistemic_score": epistemic_score,
    }

