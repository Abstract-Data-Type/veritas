import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bias_analysis
import config
import scoring

import main

client = TestClient(main.app)


# ===== Unit Tests =====


def test_load_prompts_config():
    """Test loading and parsing prompts.yaml configuration"""
    config_data = config.load_prompts_config()

    assert isinstance(config_data, list)
    assert len(config_data) > 0

    # Check structure of first dimension
    assert "name" in config_data[0]
    assert "prompt" in config_data[0]
    assert isinstance(config_data[0]["name"], str)
    assert isinstance(config_data[0]["prompt"], str)

    # Verify all four dimensions are present
    dimension_names = {dim["name"] for dim in config_data}
    expected_names = {
        "partisan_bias",
        "affective_bias",
        "framing_bias",
        "sourcing_bias",
    }
    assert dimension_names == expected_names


def test_load_prompts_config_caching():
    """Test that get_prompts_config caches the result"""
    # Reset cache
    config._PROMPTS_CONFIG = None

    config1 = config.get_prompts_config()
    config2 = config.get_prompts_config()

    # Should return same object (cached)
    assert config1 is config2


def test_parse_llm_score_valid_numbers():
    """Test parsing valid numeric responses"""
    # Valid integer
    assert bias_analysis.parse_llm_score("5") == 5.0
    assert bias_analysis.parse_llm_score("  5  ") == 5.0

    # Valid float
    assert bias_analysis.parse_llm_score("5.0") == 5.0
    assert bias_analysis.parse_llm_score("3.5") == 3.5

    # Number in text
    assert bias_analysis.parse_llm_score("The score is 5") == 5.0
    assert bias_analysis.parse_llm_score("Score: 4.0") == 4.0


def test_parse_llm_score_written_numbers():
    """Test parsing written number responses"""
    assert bias_analysis.parse_llm_score("five") == 5.0
    assert bias_analysis.parse_llm_score("The answer is seven") == 7.0
    assert bias_analysis.parse_llm_score("one") == 1.0
    assert bias_analysis.parse_llm_score("four") == 4.0


def test_parse_llm_score_clamping():
    """Test that scores are clamped to 1-7 range"""
    assert bias_analysis.parse_llm_score("7.5") == 7.0  # Clamped from above
    assert bias_analysis.parse_llm_score("0.5") == 1.0  # Clamped from below
    assert bias_analysis.parse_llm_score("10") == 7.0  # Clamped from above
    assert bias_analysis.parse_llm_score("-1") == 1.0  # Clamped from below


def test_parse_llm_score_invalid():
    """Test parsing invalid responses raises ValueError"""
    with pytest.raises(ValueError):
        bias_analysis.parse_llm_score("")

    with pytest.raises(ValueError):
        bias_analysis.parse_llm_score("   ")

    with pytest.raises(ValueError):
        bias_analysis.parse_llm_score("N/A")

    with pytest.raises(ValueError):
        bias_analysis.parse_llm_score("Unable to determine")


def test_score_bias_pass_through():
    """Test scoring function pass-through implementation"""
    raw_scores = {
        "partisan_bias": 4.0,
        "affective_bias": 3.0,
        "framing_bias": 5.0,
        "sourcing_bias": 6.0,
    }

    result = scoring.score_bias(raw_scores)

    assert result == raw_scores
    # Should be a copy, not the same object
    assert result is not raw_scores


@pytest.mark.asyncio
async def test_call_llm_for_dimension_success():
    """Test async LLM caller with successful response"""
    dimension_config = {"name": "partisan_bias", "prompt": "Rate on scale 1-7"}

    # Mock asyncio.to_thread to directly return the result
    async def mock_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("bias_analysis.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("bias_analysis._call_gemini_sync", return_value="5"):
            score = await bias_analysis.call_llm_for_dimension(
                "Test article", dimension_config
            )
            assert score == 5.0


@pytest.mark.asyncio
async def test_rate_bias_parallel_success():
    """Test parallel orchestrator with all successful calls"""
    dimension_configs = [
        {"name": "partisan_bias", "prompt": "Prompt 1"},
        {"name": "affective_bias", "prompt": "Prompt 2"},
    ]

    # Mock the async LLM caller
    async def mock_llm_call(article_text, dim_config, model):
        return 4.0

    with patch("bias_analysis.call_llm_for_dimension", side_effect=mock_llm_call):
        scores = await bias_analysis.rate_bias_parallel(
            "Test article", dimension_configs
        )

        assert len(scores) == 2
        assert scores["partisan_bias"] == 4.0
        assert scores["affective_bias"] == 4.0


@pytest.mark.asyncio
async def test_rate_bias_parallel_atomic_failure():
    """Test that parallel orchestrator fails atomically if any call fails"""
    dimension_configs = [
        {"name": "partisan_bias", "prompt": "Prompt 1"},
        {"name": "affective_bias", "prompt": "Prompt 2"},
    ]

    # Mock one call to fail
    async def mock_llm_call(article_text, dim_config, model):
        if dim_config["name"] == "partisan_bias":
            raise Exception("API failure")
        return 4.0

    with patch("bias_analysis.call_llm_for_dimension", side_effect=mock_llm_call):
        with pytest.raises(bias_analysis.HTTPException) as exc_info:
            await bias_analysis.rate_bias_parallel("Test article", dimension_configs)

        assert exc_info.value.status_code == 502
        assert "Bias rating failed" in exc_info.value.detail


# ===== Integration Tests =====


def test_rate_bias_endpoint_success():
    """Test /rate-bias endpoint with valid article text"""
    # Mock the entire parallel orchestrator
    mock_scores = {
        "partisan_bias": 4.0,
        "affective_bias": 3.0,
        "framing_bias": 5.0,
        "sourcing_bias": 6.0,
    }

    async def mock_rate_bias_parallel(article_text, dim_configs, model):
        return mock_scores

    with patch("main.rate_bias_parallel", side_effect=mock_rate_bias_parallel):
        resp = client.post(
            "/rate-bias",
            json={"article_text": "This is a test article about politics."},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "scores" in data
        assert "ai_model" in data
        assert data["scores"] == mock_scores
        assert data["ai_model"] == "gemini-2.5-flash"


def test_rate_bias_endpoint_empty_article_text():
    """Test /rate-bias endpoint with empty article_text returns 422"""
    resp = client.post("/rate-bias", json={"article_text": ""})
    assert resp.status_code == 422


def test_rate_bias_endpoint_missing_article_text():
    """Test /rate-bias endpoint with missing article_text returns 422"""
    resp = client.post("/rate-bias", json={})
    assert resp.status_code == 422


def test_rate_bias_endpoint_atomic_failure():
    """Test /rate-bias endpoint returns 502 when any LLM call fails"""

    async def mock_rate_bias_parallel_failure(article_text, dim_configs, model):
        raise bias_analysis.HTTPException(
            status_code=502,
            detail="Bias rating failed: Dimension 'partisan_bias': API error",
        )

    with patch("main.rate_bias_parallel", side_effect=mock_rate_bias_parallel_failure):
        resp = client.post("/rate-bias", json={"article_text": "Test article"})

        assert resp.status_code == 502
        assert "Bias rating failed" in resp.json()["detail"]


@patch("main.genai.Client")
def test_rate_bias_endpoint_llm_calls_count(mock_client_class):
    """Test that /rate-bias makes exactly N LLM calls (N = number of dimensions)"""
    # Setup mock
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_result = MagicMock()
    mock_result.text = "5"
    mock_client.models.generate_content.return_value = mock_result

    # Set API key
    os.environ["GEMINI_API_KEY"] = "test_key"

    try:
        resp = client.post("/rate-bias", json={"article_text": "Test article content"})

        # Should succeed
        assert resp.status_code == 200

        # Get number of dimensions from config
        config_data = config.get_prompts_config()
        num_dimensions = len(config_data)

        # Verify Gemini client was called exactly N times
        assert mock_client.models.generate_content.call_count == num_dimensions

    finally:
        # Clean up
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]


def test_rate_bias_endpoint_missing_api_key():
    """Test /rate-bias endpoint returns 500 when API key is missing"""
    # Ensure no API key
    original_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        resp = client.post("/rate-bias", json={"article_text": "Test article"})

        assert resp.status_code == 500
        assert "GEMINI_API_KEY not configured" in resp.json()["detail"]
    finally:
        # Restore original key if it existed
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
