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
    from src.models.sqlalchemy_models import Article, Summary

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
        # Create article without summary field (it's in a separate table)
        article = Article(
            title="Test Climate Bill Article",
            url="https://example.com/climate-bill-test",
            source="Test News",
            raw_text=test_article_text.strip(),
        )
        session.add(article)
        session.flush()  # Get article.article_id
        
        # Create summary in separate Summary table
        summary = Summary(
            article_id=article.article_id,
            summary_text="Senate passes climate bill with bipartisan support",
        )
        session.add(summary)
        session.commit()
        article_id = article.article_id

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


@pytest.mark.e2e
def test_full_cycle_article_workflow(backend_server, e2e_test_db):
    """
    COMPLETE END-TO-END WORKFLOW TEST
    
    This test verifies the ENTIRE backend flow from start to finish:
    1. Create an article in the database
    2. Call bias analysis endpoint → stores bias_rating with 4 dimensions
    3. Query back the stored article + bias_rating from database
    4. Verify all data is persisted correctly with new multi-dimensional structure
    5. Verify relationships are intact
    
    This tests the full database cycle with the new multi-dimensional bias scoring.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.models.sqlalchemy_models import Article, BiasRating
    
    base_url = "http://127.0.0.1:8002"
    
    # STEP 1: Create an article in database
    engine = create_engine(f"sqlite:///{e2e_test_db}")
    
    article_text = """
    Tesla reported record quarterly earnings today, driven by strong electric vehicle sales.
    The company announced a new factory in Mexico and expanded production targets.
    Competitors are accelerating EV development, with traditional automakers investing heavily.
    Environmental groups praised the shift but criticized labor practices at some facilities.
    Stock analysts remain divided on long-term profitability.
    """
    
    with Session(engine) as session:
        article = Article(
            title="Tesla Q3 Earnings Report",
            url="https://example.com/tesla-earnings",
            source="Financial News",
            raw_text=article_text.strip(),
        )
        session.add(article)
        session.flush()
        article_id = article.article_id
        session.commit()
    
    # STEP 2: Call bias analysis endpoint (makes real API calls)
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{base_url}/bias_ratings/analyze",
            json={"article_id": article_id},
        )
    
    assert resp.status_code == 200, f"Bias analysis failed: {resp.text}"
    analysis_response = resp.json()
    rating_id = analysis_response["rating_id"]
    
    # Verify response contains all 4 dimensions
    scores = analysis_response["scores"]
    assert set(scores.keys()) == {"partisan_bias", "affective_bias", "framing_bias", "sourcing_bias"}
    
    # STEP 3: Query back the article AND bias_rating from database
    with Session(engine) as session:
        # Fetch article
        stored_article = session.query(Article).filter(
            Article.article_id == article_id
        ).first()
        
        # Fetch bias rating WITH EAGER LOADING to avoid detached instance errors
        from sqlalchemy.orm import joinedload
        stored_rating = session.query(BiasRating).options(
            joinedload(BiasRating.article)
        ).filter(
            BiasRating.rating_id == rating_id
        ).first()
        
        # STEP 4: Verify article was stored correctly
        assert stored_article is not None, "Article not found in database"
        assert stored_article.title == "Tesla Q3 Earnings Report"
        assert stored_article.raw_text == article_text.strip()
        assert stored_article.source == "Financial News"
        
        # STEP 5: Verify bias rating was stored correctly with NEW MULTI-DIMENSIONAL STRUCTURE
        assert stored_rating is not None, "BiasRating not found in database"
        assert stored_rating.article_id == article_id
        
        # ✅ VERIFY NEW COLUMNS EXIST AND ARE POPULATED
        assert stored_rating.partisan_bias is not None, "partisan_bias should be stored"
        assert stored_rating.affective_bias is not None, "affective_bias should be stored"
        assert stored_rating.framing_bias is not None, "framing_bias should be stored"
        assert stored_rating.sourcing_bias is not None, "sourcing_bias should be stored"
        
        # ✅ VERIFY VALUES ARE IN VALID RANGE
        for dimension_name, dimension_value in [
            ("partisan_bias", stored_rating.partisan_bias),
            ("affective_bias", stored_rating.affective_bias),
            ("framing_bias", stored_rating.framing_bias),
            ("sourcing_bias", stored_rating.sourcing_bias),
        ]:
            assert 1.0 <= dimension_value <= 7.0, (
                f"{dimension_name} value {dimension_value} not in valid range [1.0, 7.0]"
            )
        
        # ✅ VERIFY OVERALL BIAS_SCORE IS COMPUTED AS AVERAGE
        expected_avg = (
            stored_rating.partisan_bias + 
            stored_rating.affective_bias + 
            stored_rating.framing_bias + 
            stored_rating.sourcing_bias
        ) / 4
        assert abs(stored_rating.bias_score - expected_avg) < 0.01, (
            f"bias_score {stored_rating.bias_score} should be average of 4 dimensions {expected_avg}"
        )
        
        # ✅ VERIFY RELATIONSHIP BETWEEN ARTICLE AND BIAS_RATING
        assert stored_rating.article_id == stored_article.article_id
        assert stored_rating.article is not None
        assert stored_rating.article.article_id == article_id
    


@pytest.mark.e2e
def test_database_persistence_and_retrieval(backend_server, e2e_test_db):
    """
    DATABASE PERSISTENCE TEST
    
    Verifies that:
    1. Analysis results are properly persisted to the database
    2. Data can be retrieved in the same session
    3. All 4 dimension scores are stored and retrievable
    4. Relationships work correctly
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.models.sqlalchemy_models import Article, BiasRating
    from src.models.bias_rating import (
        get_overall_bias_score,
        get_all_dimension_scores,
        get_dimension_score,
    )
    
    base_url = "http://127.0.0.1:8002"
    engine = create_engine(f"sqlite:///{e2e_test_db}")
    
    # Create multiple test articles (2 articles = ~240 seconds max, fits in e2e timeout)
    test_cases = [
        {
            "title": "Progressive Policy Article",
            "text": "Progressive policies focus on equality, social safety nets, and environmental protection...",
            "expected_lean": "progressive"
        },
        {
            "title": "Conservative Policy Article", 
            "text": "Conservative principles emphasize individual liberty, limited government, and market solutions...",
            "expected_lean": "conservative"
        },
    ]
    
    article_ids = []
    
    # Create articles
    with Session(engine) as session:
        for test_case in test_cases:
            article = Article(
                title=test_case["title"],
                url=f"https://example.com/{test_case['title'].lower().replace(' ', '-')}",
                source="Test Source",
                raw_text=test_case["text"],
            )
            session.add(article)
            session.flush()
            article_ids.append(article.article_id)
        session.commit()
    
    # Analyze each article (120 second timeout per request for parallel LLM calls)
    rating_ids = []
    with httpx.Client(timeout=120.0) as client:
        for article_id in article_ids:
            resp = client.post(
                f"{base_url}/bias_ratings/analyze",
                json={"article_id": article_id},
            )
            assert resp.status_code == 200, f"Failed to analyze article {article_id}: {resp.text}"
            rating_ids.append(resp.json()["rating_id"])
    
    # VERIFY: Query back all ratings and test utility functions
    with Session(engine) as session:
        from sqlalchemy.orm import joinedload
        for i, rating_id in enumerate(rating_ids):
            rating = session.query(BiasRating).options(
                joinedload(BiasRating.article)
            ).filter(
                BiasRating.rating_id == rating_id
            ).first()
            
            assert rating is not None, f"Rating {rating_id} not found"
            
            # ✅ Test utility functions
            # 1. Get all dimension scores
            all_scores = get_all_dimension_scores(rating)
            assert len(all_scores) == 4
            assert all(key in all_scores for key in [
                "partisan_bias", "affective_bias", "framing_bias", "sourcing_bias"
            ])
            
            # 2. Get overall score
            overall = get_overall_bias_score(rating)
            assert overall is not None
            assert 1.0 <= overall <= 7.0
            
            # 3. Get individual dimension scores
            for dimension in ["partisan_bias", "affective_bias", "framing_bias", "sourcing_bias"]:
                score = get_dimension_score(rating, dimension)
                assert score is not None
                assert 1.0 <= score <= 7.0
            
            # 4. Verify relationship
            article = rating.article
            assert article is not None
            assert article.article_id == article_ids[i]
