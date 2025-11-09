"""
Real Integration Test - Makes Actual Gemini API Calls

WARNING: This test makes real API calls to Gemini and will incur costs.
Run this only when you want to verify the actual integration works.
Requires GEMINI_API_KEY to be set in environment.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env from project root (same as main.py does)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path)

import main


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping real API integration test",
)
def test_rate_bias_real_api_integration():
    """
    Integration test that makes real API calls to Gemini.

    Verifies:
    - Endpoint returns 200 OK
    - All 4 bias dimensions are present in response
    - All scores are in valid range (1.0 - 7.0)
    - Response structure matches expected schema
    """
    client = TestClient(main.app)

    # Test article - a simple news-like text
    test_article = """
    The Senate passed a new bill today with bipartisan support. 
    The legislation, which was introduced last month, aims to address climate change 
    through a combination of renewable energy incentives and carbon reduction targets.
    Republicans and Democrats both praised the bill's balanced approach, though some 
    environmental groups argued it doesn't go far enough. The bill now moves to the House 
    for consideration.
    """

    resp = client.post("/rate-bias", json={"article_text": test_article.strip()})

    # Assert successful response
    assert (
        resp.status_code == 200
    ), f"Expected 200 OK, got {resp.status_code}: {resp.json()}"

    data = resp.json()

    # Assert response structure
    assert "scores" in data, "Response missing 'scores' field"
    assert "ai_model" in data, "Response missing 'ai_model' field"
    assert (
        data["ai_model"] == "gemini-2.5-flash"
    ), f"Expected 'gemini-2.5-flash', got '{data['ai_model']}'"

    scores = data["scores"]

    # Assert all expected dimensions are present
    expected_dimensions = {
        "partisan_bias",
        "affective_bias",
        "framing_bias",
        "sourcing_bias",
    }
    actual_dimensions = set(scores.keys())
    assert actual_dimensions == expected_dimensions, (
        f"Missing dimensions: {expected_dimensions - actual_dimensions}, "
        f"Unexpected dimensions: {actual_dimensions - expected_dimensions}"
    )

    # Assert all scores are valid floats in range 1.0-7.0
    for dimension, score in scores.items():
        assert isinstance(
            score, (int, float)
        ), f"Score for {dimension} must be numeric, got {type(score)}"
        assert (
            1.0 <= float(score) <= 7.0
        ), f"Score for {dimension} must be between 1.0 and 7.0, got {score}"

    # Assert all scores are present (not None)
    assert all(score is not None for score in scores.values()), "Some scores are None"

    # Assert scores are reasonable (not all identical, indicating potential issues)
    unique_scores = set(scores.values())
    assert len(unique_scores) > 1 or len(unique_scores) == len(
        scores
    ), "All scores are identical - may indicate an issue with API responses"
