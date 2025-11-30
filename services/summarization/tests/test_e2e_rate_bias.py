"""
End-to-End Test for /rate-bias Endpoint (DEPRECATED)

⚠️  DEPRECATED: This tests the standalone FastAPI summarization service.
    The main backend now uses the AI library directly (src/ai/).
    Use tests/test_e2e_backend.py instead for end-to-end testing.

This test starts the actual FastAPI server and makes real HTTP requests to it.
This is the closest thing to testing how a real backend client would interact with the service.

WARNING: Makes real API calls to Gemini and will incur costs.
Requires GEMINI_API_KEY to be set in environment.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path)


@pytest.fixture(scope="module")
def server_process():
    """Start the FastAPI server for E2E testing"""
    # Start uvicorn server in background
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",  # Use different port to avoid conflicts
            "--log-level",
            "error",  # Suppress server logs in test output
        ],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = httpx.get("http://127.0.0.1:8001/", timeout=1.0)
            if response.status_code == 200:
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(0.5)
    else:
        process.terminate()
        process.wait()
        pytest.fail("Server failed to start within timeout")

    yield process

    # Cleanup: stop server
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping E2E test",
)
def test_rate_bias_e2e(server_process):
    """
    End-to-end test: Makes real HTTP request to running server.

    Verifies the complete request/response cycle:
    - Server is running and accessible
    - HTTP POST request to /rate-bias
    - Response is valid JSON with correct structure
    - All 4 bias dimensions returned
    - Scores are in valid range
    """
    base_url = "http://127.0.0.1:8001"

    # Test article
    test_article = """
    The Senate passed a new bill today with bipartisan support. 
    The legislation, which was introduced last month, aims to address climate change 
    through a combination of renewable energy incentives and carbon reduction targets.
    Republicans and Democrats both praised the bill's balanced approach, though some 
    environmental groups argued it doesn't go far enough. The bill now moves to the House 
    for consideration.
    """

    # Make real HTTP request to running server
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{base_url}/rate-bias", json={"article_text": test_article.strip()}
        )

    # Assert successful HTTP response
    assert (
        resp.status_code == 200
    ), f"Expected 200 OK, got {resp.status_code}: {resp.text}"

    # Parse JSON response
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


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping E2E test",
)
def test_rate_bias_e2e_error_handling(server_process):
    """E2E test for error handling - empty article text"""
    base_url = "http://127.0.0.1:8001"

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(f"{base_url}/rate-bias", json={"article_text": ""})

    # Should return validation error
    assert (
        resp.status_code == 422
    ), f"Expected 422 validation error, got {resp.status_code}: {resp.text}"


@pytest.mark.e2e
def test_rate_bias_e2e_server_health(server_process):
    """E2E test: Verify server health endpoint works"""
    base_url = "http://127.0.0.1:8001"

    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{base_url}/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "service" in data
