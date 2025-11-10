"""
Unit tests for bias rating analyze endpoint.
Tests the /analyze endpoint that calls the LLM service and stores results.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.sqlalchemy import Base
from src.main import app
from src.models.sqlalchemy_models import Article, BiasRating


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
            created_at=datetime.utcnow(),
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
        from src.db.sqlalchemy import get_session

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
            created_at=datetime.utcnow(),
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)

        from src.db.sqlalchemy import get_session

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
        # Create existing bias rating
        existing_rating = BiasRating(
            article_id=1,
            bias_score=0.5,
            reasoning="Existing analysis",
            evaluated_at=datetime.utcnow(),
        )
        test_db.add(existing_rating)
        test_db.commit()
        test_db.refresh(existing_rating)

        from src.db.sqlalchemy import get_session

        def override_get_session():
            try:
                yield test_db
            finally:
                pass

        app.dependency_overrides[get_session] = override_get_session

        try:
            response = client.post("/bias_ratings/analyze", json={"article_id": 1})

            # Should return existing rating without calling the service
            assert response.status_code == 200
            data = response.json()
            assert data["rating_id"] == existing_rating.rating_id
            assert data["bias_score"] == 0.5
            assert data["reasoning"] == "Existing analysis"
        finally:
            app.dependency_overrides.clear()


class TestDatabaseOperations:
    """Test database-level bias rating operations"""

    def test_create_bias_rating_directly(self, test_db):
        """Test creating a bias rating directly in the database"""
        rating = BiasRating(
            article_id=1,
            bias_score=0.7,
            reasoning="Test direct creation",
            evaluated_at=datetime.utcnow(),
        )
        test_db.add(rating)
        test_db.commit()
        test_db.refresh(rating)

        assert rating.rating_id is not None
        assert rating.article_id == 1
        assert rating.bias_score == 0.7

    def test_query_bias_rating_by_article(self, test_db):
        """Test querying bias ratings by article_id"""
        # Create a rating
        rating = BiasRating(
            article_id=1,
            bias_score=0.2,
            reasoning="Test query",
            evaluated_at=datetime.utcnow(),
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
