import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai import rate_bias, rate_secm, summarize_with_gemini
from ..db.sqlalchemy import get_session
from ..models.bias_rating import (
    get_all_dimension_scores,
    get_overall_bias_score,
    normalize_score_to_range,
)
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
    bias_score: float | None
    reasoning: str
    scores: dict[str, float]
    # Multi-dimensional scores (legacy 4-dimension system)
    partisan_bias: float | None = None
    affective_bias: float | None = None
    framing_bias: float | None = None
    sourcing_bias: float | None = None
    # SECM scores (new system)
    secm_ideological_score: float | None = None
    secm_epistemic_score: float | None = None


@router.post("/analyze", response_model=AnalyzeArticleResponse)
async def analyze_article_bias(
    request: AnalyzeArticleRequest, db: Session = Depends(get_session)
):
    """
    Analyze an article for political bias using the AI library.

    This endpoint is called by the worker after storing a new article.
    It fetches the article text, calls the bias rating function, and stores the results.

    Args:
        request: Contains article_id to analyze

    Returns:
        The created bias rating with scores

    Raises:
        HTTPException: If article not found or bias analysis fails
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
        dimension_scores = get_all_dimension_scores(existing_rating)
        overall_score = get_overall_bias_score(existing_rating)
        # Normalize the score from 1-7 scale to -1 to 1 scale for API response
        normalized_score = normalize_score_to_range(overall_score) if overall_score is not None else None
        return AnalyzeArticleResponse(
            rating_id=existing_rating.rating_id,
            article_id=existing_rating.article_id,
            bias_score=normalized_score,
            reasoning=existing_rating.reasoning or "",
            scores=dimension_scores,
            partisan_bias=existing_rating.partisan_bias,
            affective_bias=existing_rating.affective_bias,
            framing_bias=existing_rating.framing_bias,
            sourcing_bias=existing_rating.sourcing_bias,
            secm_ideological_score=existing_rating.secm_ideological_score,
            secm_epistemic_score=existing_rating.secm_epistemic_score,
        )

    # Call both bias rating systems
    try:
        logger.info(f"Calling bias analysis for article {request.article_id}")
        
        # Run existing 4-dimension analysis (backward compatibility)
        bias_result = await rate_bias(article.raw_text)

        # Extract scores from result
        scores = bias_result.get("scores", {})

        # Extract individual dimension scores (on 1-7 scale)
        partisan_bias = scores.get("partisan_bias")
        affective_bias = scores.get("affective_bias")
        framing_bias = scores.get("framing_bias")
        sourcing_bias = scores.get("sourcing_bias")

        # Calculate overall bias score as average of dimensions, then normalize to -1 to 1
        valid_scores = [s for s in [partisan_bias, affective_bias, framing_bias, sourcing_bias] if s is not None]
        if valid_scores:
            avg_score = sum(valid_scores) / len(valid_scores)
            overall_bias_score = normalize_score_to_range(avg_score)  # Convert 1-7 to -1 to 1
        else:
            overall_bias_score = None

        # Run new SECM analysis (22 parallel LLM calls)
        logger.info(f"Calling SECM analysis for article {request.article_id}")
        secm_result = await rate_secm(article.raw_text)

        # Extract SECM scores
        secm_ideological_score = secm_result.get("ideological_score")
        secm_epistemic_score = secm_result.get("epistemic_score")
        secm_variables = secm_result.get("variables", {})
        secm_reasoning = secm_result.get("reasoning", {})

        # Store the bias rating with all dimensions (both old and new systems)
        new_rating = BiasRating(
            article_id=request.article_id,
            bias_score=overall_bias_score,
            # Existing 4-dimension scores
            partisan_bias=partisan_bias,
            affective_bias=affective_bias,
            framing_bias=framing_bias,
            sourcing_bias=sourcing_bias,
            reasoning=None,
            evaluated_at=datetime.now(UTC),
            # SECM scores
            secm_ideological_score=secm_ideological_score,
            secm_epistemic_score=secm_epistemic_score,
            # SECM binary variables (all 22)
            secm_ideol_l1_systemic_naming=secm_variables.get("secm_ideol_l1_systemic_naming"),
            secm_ideol_l2_power_gap_lexicon=secm_variables.get("secm_ideol_l2_power_gap_lexicon"),
            secm_ideol_l3_elite_culpability=secm_variables.get("secm_ideol_l3_elite_culpability"),
            secm_ideol_l4_resource_redistribution=secm_variables.get("secm_ideol_l4_resource_redistribution"),
            secm_ideol_l5_change_as_justice=secm_variables.get("secm_ideol_l5_change_as_justice"),
            secm_ideol_l6_care_harm=secm_variables.get("secm_ideol_l6_care_harm"),
            secm_ideol_r1_agentic_culpability=secm_variables.get("secm_ideol_r1_agentic_culpability"),
            secm_ideol_r2_order_lexicon=secm_variables.get("secm_ideol_r2_order_lexicon"),
            secm_ideol_r3_institutional_defense=secm_variables.get("secm_ideol_r3_institutional_defense"),
            secm_ideol_r4_meritocratic_defense=secm_variables.get("secm_ideol_r4_meritocratic_defense"),
            secm_ideol_r5_change_as_threat=secm_variables.get("secm_ideol_r5_change_as_threat"),
            secm_ideol_r6_sanctity_degradation=secm_variables.get("secm_ideol_r6_sanctity_degradation"),
            secm_epist_h1_primary_documentation=secm_variables.get("secm_epist_h1_primary_documentation"),
            secm_epist_h2_adversarial_sourcing=secm_variables.get("secm_epist_h2_adversarial_sourcing"),
            secm_epist_h3_specific_attribution=secm_variables.get("secm_epist_h3_specific_attribution"),
            secm_epist_h4_data_contextualization=secm_variables.get("secm_epist_h4_data_contextualization"),
            secm_epist_h5_methodological_transparency=secm_variables.get("secm_epist_h5_methodological_transparency"),
            secm_epist_e1_emotive_adjectives=secm_variables.get("secm_epist_e1_emotive_adjectives"),
            secm_epist_e2_labeling_othering=secm_variables.get("secm_epist_e2_labeling_othering"),
            secm_epist_e3_causal_certainty=secm_variables.get("secm_epist_e3_causal_certainty"),
            secm_epist_e4_imperative_direct_address=secm_variables.get("secm_epist_e4_imperative_direct_address"),
            secm_epist_e5_motivated_reasoning=secm_variables.get("secm_epist_e5_motivated_reasoning"),
            secm_reasoning_json=json.dumps(secm_reasoning) if secm_reasoning else None,
        )

        db.add(new_rating)
        db.flush()  # Flush to get rating_id without full commit

        # Get rating_id after flush (it's populated by autoincrement)
        rating_id = new_rating.rating_id

        # Now commit the transaction
        db.commit()

        logger.info(
            f"Stored bias rating {rating_id} for article {request.article_id} "
            f"with scores: partisan={partisan_bias}, affective={affective_bias}, "
            f"framing={framing_bias}, sourcing={sourcing_bias}, "
            f"SECM ideological={secm_ideological_score}, SECM epistemic={secm_epistemic_score}"
        )

        return AnalyzeArticleResponse(
            rating_id=rating_id,
            article_id=request.article_id,
            bias_score=overall_bias_score,
            reasoning="",
            scores=scores,
            partisan_bias=partisan_bias,
            affective_bias=affective_bias,
            framing_bias=framing_bias,
            sourcing_bias=sourcing_bias,
            secm_ideological_score=secm_ideological_score,
            secm_epistemic_score=secm_epistemic_score,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 502 from rate_bias)
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing bias: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze article bias: {str(e)}"
        )


@router.post("/summarize")
async def summarize_article(request: SummarizeRequest):
    """
    Summarize article text using the AI library.

    This endpoint validates the input and calls the summarization function directly.

    Args:
        request: Contains article_text to summarize

    Returns:
        Dictionary with 'summary' key containing the summarized text

    Raises:
        HTTPException: 422 for invalid input, 500/502 for errors
    """
    # Validate article text
    if not request.article_text or not request.article_text.strip():
        raise HTTPException(
            status_code=422, detail="Article text is required and cannot be empty"
        )

    try:
        logger.info("Calling summarization function")
        summary = summarize_with_gemini(request.article_text)

        if not summary or not summary.strip():
            logger.error("Summarization function returned empty summary")
            raise HTTPException(
                status_code=502, detail="Summarization returned empty summary"
            )

        return {"summary": summary}

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 500/502 from summarize_with_gemini)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to summarize article: {str(e)}"
        )
