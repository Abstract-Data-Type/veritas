"""
Unit tests for bias rating analyze endpoint.
Tests the /analyze endpoint that calls the AI library functions and stores results.
"""

from datetime import UTC, datetime
import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base
from veritas_news.main import app
from veritas_news.models.sqlalchemy_models import Article, BiasRating


@pytest.fixture
def test_db():
    """Create an in-memory test database with sample data using SQLAlchemy"""
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create a session
    db = TestSessionLocal()

    try:
        # Insert test article with content
        test_article = Article(
            title="Test Article",
            source="Test Source",
            url="https://test.com/article",
            raw_text="This is test article content for bias analysis.",
            created_at=datetime.now(UTC),
        )
        db.add(test_article)
        db.commit()
        db.refresh(test_article)

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestAnalyzeEndpoint:
    """Test the /bias_ratings/analyze endpoint"""

    def test_analyze_article_not_found(self, test_db, client):
        """Test analyzing a non-existent article"""
        from veritas_news.db.sqlalchemy import get_session

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post("/bias_ratings/analyze", json={"article_id": 999})
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_analyze_article_no_content(self, test_db, client):
        """Test analyzing an article with no text content"""
        # Create article without raw_text
        article = Article(
            title="Empty Article",
            source="Test",
            url="https://test.com/empty",
            raw_text="",
            created_at=datetime.now(UTC),
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)

        from veritas_news.db.sqlalchemy import get_session

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post(
                "/bias_ratings/analyze", json={"article_id": article.article_id}
            )
            assert response.status_code == 422
            assert "no text content" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_analyze_returns_existing_rating(self, test_db, client):
        """Test that analyzing an already-analyzed article returns existing rating"""
        # Create existing bias rating with multi-dimensional scores
        existing_rating = BiasRating(
            article_id=1,
            bias_score=4.5,
            partisan_bias=3.0,
            affective_bias=4.0,
            framing_bias=5.0,
            sourcing_bias=6.0,
            reasoning="Existing analysis",
            evaluated_at=datetime.now(UTC),
        )
        test_db.add(existing_rating)
        test_db.commit()
        test_db.refresh(existing_rating)

        from veritas_news.db.sqlalchemy import get_session

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post("/bias_ratings/analyze", json={"article_id": 1})

            # Should return existing rating without calling the AI function
            assert response.status_code == 200
            data = response.json()
            assert data["rating_id"] == existing_rating.rating_id
            # bias_score is normalized from 1-7 scale to -1 to 1 scale
            # Average of (3+4+5+6)/4 = 4.5, normalized: (4.5-4)/3 = 0.167
            assert abs(data["bias_score"] - 0.167) < 0.01
            assert data["reasoning"] == "Existing analysis"
            # Verify multi-dimensional scores
            assert data["partisan_bias"] == 3.0
            assert data["affective_bias"] == 4.0
            assert data["framing_bias"] == 5.0
            assert data["sourcing_bias"] == 6.0
        finally:
            app.dependency_overrides.clear()

    @patch("veritas_news.ai.bias_analysis.genai.Client")
    def test_analyze_success(self, mock_client_class, test_db, client):
        """Test successful bias analysis - integration test with mocked Gemini API"""
        from veritas_news.db.sqlalchemy import get_session

        # Mock the Gemini client (external API)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = "5"  # LLM returns score as text
        mock_client.models.generate_content.return_value = mock_result

        # Set API key
        original_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test_key"

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post("/bias_ratings/analyze", json={"article_id": 1})

            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == 1
            assert "rating_id" in data
            # Verify multi-dimensional scores are present
            assert "partisan_bias" in data
            assert "affective_bias" in data
            assert "framing_bias" in data
            assert "sourcing_bias" in data
            # All scores should be 5.0 (from mock)
            assert data["partisan_bias"] == 5.0
            assert data["affective_bias"] == 5.0
            assert data["framing_bias"] == 5.0
            assert data["sourcing_bias"] == 5.0
            # Overall bias score is normalized from 1-7 scale to -1 to 1 scale
            # Average of all dimensions is 5.0, normalized: (5.0-4)/3 = 0.333
            assert abs(data["bias_score"] - 0.333) < 0.01
            # Verify Gemini was called (for each dimension - 4 times)
            assert mock_client.models.generate_content.call_count == 4
        finally:
            app.dependency_overrides.clear()
            # Restore original key
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
            elif "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

    @patch("veritas_news.ai.bias_analysis.genai.Client")
    def test_analyze_gemini_api_failure(self, mock_client_class, test_db, client):
        """Test that Gemini API failure returns 502"""
        from veritas_news.db.sqlalchemy import get_session

        # Mock Gemini API to raise error
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API timeout")

        original_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test_key"

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post("/bias_ratings/analyze", json={"article_id": 1})

            assert response.status_code == 502
            assert "Bias rating failed" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
            # Restore original key
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
            elif "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]


class TestDatabaseOperations:
    """Test database-level bias rating operations"""

    def test_create_bias_rating_directly(self, test_db):
        """Test creating a bias rating directly in the database with multi-dimensional scores"""
        rating = BiasRating(
            article_id=1,
            bias_score=4.5,
            partisan_bias=3.0,
            affective_bias=4.0,
            framing_bias=5.0,
            sourcing_bias=6.0,
            reasoning="Test direct creation",
            evaluated_at=datetime.now(UTC),
        )
        test_db.add(rating)
        test_db.commit()
        test_db.refresh(rating)

        assert rating.rating_id is not None
        assert rating.article_id == 1
        assert rating.bias_score == 4.5
        assert rating.partisan_bias == 3.0
        assert rating.affective_bias == 4.0
        assert rating.framing_bias == 5.0
        assert rating.sourcing_bias == 6.0

    def test_query_bias_rating_by_article(self, test_db):
        """Test querying bias ratings by article_id"""
        # Create a rating
        rating = BiasRating(
            article_id=1,
            bias_score=0.2,
            reasoning="Test query",
            evaluated_at=datetime.now(UTC),
        )
        test_db.add(rating)
        test_db.commit()

        # Query it back
        result = test_db.query(BiasRating).filter(BiasRating.article_id == 1).first()

        assert result is not None
        assert result.article_id == 1
        assert result.bias_score == 0.2


if __name__ == "__main__":
    pytest.main([__file__])
