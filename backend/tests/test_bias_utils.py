"""Tests for bias rating utility functions."""

import pytest

from veritas_news.models.bias_rating import (
    get_all_dimension_scores,
    get_dimension_score,
    get_overall_bias_score,
)
from veritas_news.models.sqlalchemy_models import BiasRating


def test_get_overall_bias_score_all_dimensions():
    """Test overall score calculation with all 4 dimensions present."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=4.0,
        framing_bias=5.0,
        sourcing_bias=6.0,
    )

    overall = get_overall_bias_score(rating)
    assert overall == 4.5  # (3+4+5+6)/4


def test_get_overall_bias_score_partial_dimensions():
    """Test overall score calculation with some null dimensions."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=None,
        framing_bias=5.0,
        sourcing_bias=None,
    )

    overall = get_overall_bias_score(rating)
    assert overall == 4.0  # (3+5)/2


def test_get_overall_bias_score_all_null():
    """Test overall score calculation with all null dimensions."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=None,
        affective_bias=None,
        framing_bias=None,
        sourcing_bias=None,
    )

    overall = get_overall_bias_score(rating)
    assert overall is None


def test_get_overall_bias_score_edge_values():
    """Test overall score calculation with edge values."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=1.0,
        affective_bias=7.0,
        framing_bias=1.0,
        sourcing_bias=7.0,
    )

    overall = get_overall_bias_score(rating)
    assert overall == 4.0  # (1+7+1+7)/4


def test_get_all_dimension_scores():
    """Test retrieving all dimension scores as dictionary."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=4.0,
        framing_bias=5.0,
        sourcing_bias=6.0,
    )

    scores = get_all_dimension_scores(rating)

    assert scores == {
        "partisan_bias": 3.0,
        "affective_bias": 4.0,
        "framing_bias": 5.0,
        "sourcing_bias": 6.0,
    }


def test_get_all_dimension_scores_with_nulls():
    """Test retrieving dimension scores with null values."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=None,
        framing_bias=5.0,
        sourcing_bias=None,
    )

    scores = get_all_dimension_scores(rating)

    assert scores == {
        "partisan_bias": 3.0,
        "affective_bias": None,
        "framing_bias": 5.0,
        "sourcing_bias": None,
    }


def test_get_dimension_score_valid():
    """Test getting individual dimension score with valid dimension name."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=4.0,
        framing_bias=5.0,
        sourcing_bias=6.0,
    )

    assert get_dimension_score(rating, "partisan_bias") == 3.0
    assert get_dimension_score(rating, "affective_bias") == 4.0
    assert get_dimension_score(rating, "framing_bias") == 5.0
    assert get_dimension_score(rating, "sourcing_bias") == 6.0


def test_get_dimension_score_null():
    """Test getting null dimension score."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=None,
        affective_bias=4.0,
        framing_bias=None,
        sourcing_bias=6.0,
    )

    assert get_dimension_score(rating, "partisan_bias") is None
    assert get_dimension_score(rating, "framing_bias") is None


def test_get_dimension_score_invalid():
    """Test getting dimension score with invalid dimension name."""
    rating = BiasRating(
        article_id=1,
        partisan_bias=3.0,
        affective_bias=4.0,
        framing_bias=5.0,
        sourcing_bias=6.0,
    )

    with pytest.raises(ValueError, match="Invalid dimension"):
        get_dimension_score(rating, "invalid_dimension")

    with pytest.raises(ValueError, match="Invalid dimension"):
        get_dimension_score(rating, "bias_score")

