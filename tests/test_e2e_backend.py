"""
End-to-End Test for Backend Application

This test starts the actual FastAPI backend server and makes real HTTP requests to it.
This is the closest thing to testing how a user would interact with the application.

The backend now uses the AI library directly (no separate microservice).

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
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path)


@pytest.fixture(scope="module")
def e2e_test_db():
    """Create a test database for E2E testing"""
    import tempfile
    from sqlalchemy import create_engine
    from src.models.sqlalchemy_models import Base

    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create tables
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    yield db_path

    # Cleanup: remove test database
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="module")
def backend_server(e2e_test_db):
    """Start the main backend FastAPI server for E2E testing with test database"""
    # Set DB_PATH so backend uses test database
    old_db_path = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = e2e_test_db

    # Start uvicorn server in background
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",  # Use different port to avoid conflicts
            "--log-level",
            "error",  # Suppress server logs in test output
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),  # Pass environment including DB_PATH
    )

    # Wait for server to start
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = httpx.get("http://127.0.0.1:8002/", timeout=1.0)
            if response.status_code == 200:
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(0.5)
    else:
        process.terminate()
        process.wait()
        pytest.fail("Backend server failed to start within timeout")

    yield process

    # Cleanup: stop server
    process.terminate()
    process.wait(timeout=5)

    # Restore original DB_PATH
    if old_db_path:
        os.environ["DB_PATH"] = old_db_path
    elif "DB_PATH" in os.environ:
        del os.environ["DB_PATH"]


@pytest.mark.e2e
def test_backend_health(backend_server):
    """E2E test: Verify backend server health endpoint works"""
    base_url = "http://127.0.0.1:8002"

    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{base_url}/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "message" in data


@pytest.mark.e2e
def test_summarize_e2e(backend_server):
    """
    End-to-end test for summarization: Makes real HTTP request to running server.

    Verifies the complete request/response cycle:
    - Server is running and accessible
    - POST to /bias_ratings/summarize endpoint
    - AI library is called (makes real Gemini API call)
    - Response is valid JSON with correct structure
    - Summary is generated
    """
    base_url = "http://127.0.0.1:8002"

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
            f"{base_url}/bias_ratings/summarize",
            json={"article_text": test_article.strip()},
        )

    # Assert successful HTTP response
    assert (
        resp.status_code == 200
    ), f"Expected 200 OK, got {resp.status_code}: {resp.text}"

    # Parse JSON response
    data = resp.json()

    # Assert response structure
    assert "summary" in data, "Response missing 'summary' field"
    
    # Assert summary is not empty
    summary = data["summary"]
    assert summary, "Summary should not be empty"
    assert isinstance(summary, str), "Summary should be a string"
    assert len(summary) > 10, "Summary should be meaningful (> 10 chars)"


@pytest.mark.e2e
def test_summarize_e2e_validation_error(backend_server):
    """E2E test for error handling - empty article text"""
    base_url = "http://127.0.0.1:8002"

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{base_url}/bias_ratings/summarize", json={"article_text": ""}
        )

    # Should return validation error
    assert (
        resp.status_code == 422
    ), f"Expected 422 validation error, got {resp.status_code}: {resp.text}"


@pytest.mark.e2e
def test_bias_analysis_e2e_with_real_article(backend_server, e2e_test_db):
    """
    End-to-end test for bias analysis: Complete flow with database.

    This test verifies the complete flow:
    1. Create an article directly in the test database (same DB backend uses)
    2. Call /bias_ratings/analyze endpoint via HTTP
    3. AI library is called (makes real Gemini API calls)
    4. Results are stored in database
    5. Response includes all bias dimensions with valid scores

    This is a true end-to-end test that exercises the full stack.
    """
    base_url = "http://127.0.0.1:8002"

    # Create an article in the same database the backend uses
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.models.sqlalchemy_models import Article

    engine = create_engine(f"sqlite:///{e2e_test_db}")

    test_article_text = """
    The Senate passed a new bill today with bipartisan support. 
    The legislation, which was introduced last month, aims to address climate change 
    through a combination of renewable energy incentives and carbon reduction targets.
    Republicans and Democrats both praised the bill's balanced approach, though some 
    environmental groups argued it doesn't go far enough. The bill now moves to the House 
    for consideration. The bill includes provisions for solar panel subsidies and wind 
    energy development.
    """

    with Session(engine) as session:
        article = Article(
            title="Test Climate Bill Article",
            url="https://example.com/climate-bill-test",
            source="Test News",
            raw_text=test_article_text.strip(),
            summary="Senate passes climate bill with bipartisan support",
        )
        session.add(article)
        session.commit()
        article_id = article.id

    # Make real HTTP request to running server for bias analysis
    with httpx.Client(timeout=120.0) as client:  # Longer timeout for parallel LLM calls
        resp = client.post(
            f"{base_url}/bias_ratings/analyze",
            json={"article_id": article_id},
        )

    # Verify successful response
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert "rating_id" in data, "Response missing 'rating_id'"
    assert "article_id" in data, "Response missing 'article_id'"
    assert data["article_id"] == article_id
    assert "scores" in data, "Response missing 'scores'"

    # Verify all bias dimensions are present and valid
    scores = data["scores"]
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

    # Verify all scores are valid
    for dimension, score in scores.items():
        assert isinstance(
            score, (int, float)
        ), f"Score for {dimension} must be numeric, got {type(score)}"
        assert (
            1.0 <= float(score) <= 7.0
        ), f"Score for {dimension} must be between 1.0 and 7.0, got {score}"


@pytest.mark.e2e
def test_bias_analysis_e2e_article_not_found(backend_server):
    """E2E test: Verify proper error handling when article doesn't exist"""
    base_url = "http://127.0.0.1:8002"

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{base_url}/bias_ratings/analyze", json={"article_id": 99999}
        )

    # Should return 404 (article not found)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

