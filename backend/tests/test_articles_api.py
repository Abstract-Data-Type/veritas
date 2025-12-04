"""
Tests for the articles API endpoints.

Tests filtering, pagination, and response structure for /articles/latest endpoint.
"""

from datetime import UTC, datetime, timedelta
import os
import tempfile

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base, get_session
from veritas_news.main import app
from veritas_news.models.sqlalchemy_models import Article, BiasRating


@pytest.fixture
def test_db():
    """Create a temporary database for testing"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Set environment variable
    os.environ["DB_PATH"] = db_path
    os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{db_path}"

    # Create engine and tables
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield TestingSessionLocal, db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(test_db):
    """Create test client with test database"""
    TestingSessionLocal, db_path = test_db

    def override_get_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_articles(test_db):
    """Create sample articles with varying dates and bias scores"""
    TestingSessionLocal, _ = test_db
    db = TestingSessionLocal()

    now = datetime.now(UTC)

    articles = [
        # Recent neutral article
        Article(
            title="Tech News Update",
            source="TechDaily",
            url="https://example.com/tech1",
            published_at=now - timedelta(hours=2),
            raw_text="Technology news content",
            created_at=now - timedelta(hours=2),
        ),
        # Week-old conservative article
        Article(
            title="Economic Policy Analysis",
            source="NewsSource",
            url="https://example.com/econ1",
            published_at=now - timedelta(days=7),
            raw_text="Economic policy content",
            created_at=now - timedelta(days=7),
        ),
        # Month-old progressive article
        Article(
            title="Climate Action Report",
            source="GreenNews",
            url="https://example.com/climate1",
            published_at=now - timedelta(days=30),
            raw_text="Climate action content",
            created_at=now - timedelta(days=30),
        ),
        # Recent article without bias rating
        Article(
            title="Breaking News",
            source="NewsWire",
            url="https://example.com/breaking1",
            published_at=now - timedelta(hours=1),
            raw_text="Breaking news content",
            created_at=now - timedelta(hours=1),
        ),
    ]

    for article in articles:
        db.add(article)
    db.commit()

    # Add bias ratings to first 3 articles
    bias_ratings = [
        BiasRating(
            article_id=articles[0].article_id,
            bias_score=0.1,  # Neutral
            reasoning="Balanced reporting",
            evaluated_at=now,
        ),
        BiasRating(
            article_id=articles[1].article_id,
            bias_score=0.6,  # Conservative
            reasoning="Conservative perspective",
            evaluated_at=now,
        ),
        BiasRating(
            article_id=articles[2].article_id,
            bias_score=-0.7,  # Progressive
            reasoning="Progressive perspective",
            evaluated_at=now,
        ),
    ]

    for rating in bias_ratings:
        db.add(rating)
    db.commit()

    db.close()
    return articles


class TestArticlesLatestEndpoint:
    """Test suite for /articles/latest endpoint"""

    def test_get_latest_articles_basic(self, client, sample_articles):
        """Test basic retrieval of latest articles"""
        response = client.get("/articles/latest")

        assert response.status_code == 200
        data = response.json()

        assert "articles" in data
        assert "total" in data
        assert len(data["articles"]) == 4  # All 4 sample articles
        assert data["total"] == 4

        # Verify response structure
        article = data["articles"][0]
        assert "article_id" in article
        assert "title" in article
        assert "source" in article
        assert "url" in article
        assert "published_at" in article
        assert "created_at" in article
        assert "bias_rating" in article

    def test_filter_by_date_range(self, client, sample_articles):
        """Test filtering articles by date range"""
        from urllib.parse import quote

        now = datetime.now(UTC)

        # Get articles from last 3 days
        start_date = (now - timedelta(days=3)).isoformat()
        response = client.get(f"/articles/latest?start_date={quote(start_date)}")

        assert response.status_code == 200
        data = response.json()

        # Should only get the 2 recent articles (2 hours and 1 hour ago)
        assert data["total"] == 2

        # Get articles older than 5 days
        end_date = (now - timedelta(days=5)).isoformat()
        response = client.get(f"/articles/latest?end_date={quote(end_date)}")

        assert response.status_code == 200
        data = response.json()

        # Should get articles from 7 and 30 days ago
        assert data["total"] == 2

    def test_filter_by_bias_score(self, client, sample_articles):
        """Test filtering articles by bias score range"""
        # Get neutral articles (bias score between -0.3 and 0.3)
        response = client.get("/articles/latest?min_bias_score=-0.3&max_bias_score=0.3")

        assert response.status_code == 200
        data = response.json()

        # Should only get the neutral article
        assert data["total"] == 1
        assert data["articles"][0]["bias_rating"]["bias_score"] == 0.1

        # Get conservative-leaning articles (bias score > 0.5)
        response = client.get("/articles/latest?min_bias_score=0.5")

        assert response.status_code == 200
        data = response.json()

        # Should only get the conservative article
        assert data["total"] == 1
        assert data["articles"][0]["bias_rating"]["bias_score"] == 0.6

        # Get progressive-leaning articles (bias score < -0.5)
        response = client.get("/articles/latest?max_bias_score=-0.5")

        assert response.status_code == 200
        data = response.json()

        # Should only get the progressive article
        assert data["total"] == 1
        assert data["articles"][0]["bias_rating"]["bias_score"] == -0.7

    def test_pagination(self, client, sample_articles):
        """Test pagination with offset and limit"""
        # Get first 2 articles
        response = client.get("/articles/latest?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()

        assert len(data["articles"]) == 2
        first_page_ids = [a["article_id"] for a in data["articles"]]

        # Get next 2 articles
        response = client.get("/articles/latest?limit=2&offset=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["articles"]) == 2
        second_page_ids = [a["article_id"] for a in data["articles"]]

        # Ensure no overlap between pages
        assert set(first_page_ids).isdisjoint(set(second_page_ids))

    def test_combined_filters(self, client, sample_articles):
        """Test combining multiple filters"""
        from urllib.parse import quote

        now = datetime.now(UTC)
        start_date = (now - timedelta(days=10)).isoformat()

        # Get recent articles with conservative bias
        response = client.get(
            f"/articles/latest?start_date={quote(start_date)}&min_bias_score=0.5"
        )

        assert response.status_code == 200
        data = response.json()

        # Should get the conservative article from 7 days ago
        assert data["total"] == 1
        assert data["articles"][0]["bias_rating"]["bias_score"] == 0.6

    def test_empty_results(self, client, sample_articles):
        """Test that endpoint handles no matching results gracefully"""
        # Query for impossible bias score range
        response = client.get("/articles/latest?min_bias_score=0.9&max_bias_score=1.0")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["articles"] == []

    def test_invalid_parameters(self, client, sample_articles):
        """Test validation of query parameters"""
        # Invalid bias score (out of range)
        response = client.get("/articles/latest?min_bias_score=2.0")

        assert response.status_code == 422  # Validation error

        # Invalid limit (too large)
        response = client.get("/articles/latest?limit=200")

        assert response.status_code == 422  # Validation error

        # Invalid offset (negative)
        response = client.get("/articles/latest?offset=-1")

        assert response.status_code == 422  # Validation error
