"""
Tests for the 12-hour maintenance cycle and status endpoint.

Tests:
- /status endpoint returns correct maintenance state
- maintenance_state can be toggled
- Database clear and refetch cycle works correctly
- Article processing with LLM analysis integration
"""

import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
import os
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base, get_session
from veritas_news.main import app, maintenance_state
from veritas_news.models.sqlalchemy_models import Article, BiasRating, Summary
from veritas_news.worker.news_worker import NewsWorker


@pytest.fixture
def test_db():
    """Create a temporary database for testing"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield TestingSessionLocal, db_path, engine

    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(test_db):
    """Create test client with test database"""
    TestingSessionLocal, db_path, engine = test_db

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
    """Create sample articles in the test database"""
    TestingSessionLocal, _, _ = test_db
    db = TestingSessionLocal()

    now = datetime.now(UTC)
    articles = [
        Article(
            title="Test Article 1",
            source="TestSource",
            url="https://example.com/test1",
            published_at=now,
            raw_text="This is test article content for testing purposes.",
            created_at=now,
        ),
        Article(
            title="Test Article 2",
            source="TestSource",
            url="https://example.com/test2",
            published_at=now,
            raw_text="Another test article with different content.",
            created_at=now,
        ),
    ]

    for article in articles:
        db.add(article)
    db.commit()
    db.close()
    return articles


@contextmanager
def mock_get_connection(TestingSessionLocal):
    """Context manager to mock get_connection with test database"""
    @contextmanager
    def _get_connection():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    with patch("veritas_news.worker.news_worker.get_connection", _get_connection):
        yield


class TestStatusEndpoint:
    """Test suite for /status endpoint"""

    def test_status_endpoint_returns_200(self, client):
        """Test that /status endpoint is accessible"""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_response_structure(self, client):
        """Test that /status returns correct structure"""
        response = client.get("/status")
        data = response.json()

        assert "status" in data
        assert "maintenance" in data
        assert data["status"] == "ok"

        maintenance = data["maintenance"]
        assert "is_running" in maintenance
        assert "started_at" in maintenance
        assert "last_completed" in maintenance
        assert "next_refresh" in maintenance

    def test_maintenance_state_defaults(self, client):
        """Test that maintenance state has correct defaults"""
        # Reset to defaults for test
        maintenance_state["is_running"] = False
        maintenance_state["started_at"] = None
        maintenance_state["last_completed"] = None
        maintenance_state["next_refresh"] = None

        response = client.get("/status")
        data = response.json()

        assert data["maintenance"]["is_running"] is False
        assert data["maintenance"]["started_at"] is None


class TestMaintenanceStateToggle:
    """Test maintenance state manipulation"""

    def test_maintenance_state_can_be_set_to_running(self, client):
        """Test that maintenance state can be set to running"""
        maintenance_state["is_running"] = True
        maintenance_state["started_at"] = datetime.now(UTC).isoformat()

        response = client.get("/status")
        data = response.json()

        assert data["maintenance"]["is_running"] is True
        assert data["maintenance"]["started_at"] is not None

    def test_maintenance_state_can_be_set_to_not_running(self, client):
        """Test that maintenance state can be set to not running"""
        maintenance_state["is_running"] = False
        maintenance_state["last_completed"] = datetime.now(UTC).isoformat()

        response = client.get("/status")
        data = response.json()

        assert data["maintenance"]["is_running"] is False
        assert data["maintenance"]["last_completed"] is not None

    def test_maintenance_state_persists_across_requests(self, client):
        """Test that maintenance state persists between requests"""
        maintenance_state["is_running"] = True

        response1 = client.get("/status")
        response2 = client.get("/status")

        assert response1.json()["maintenance"]["is_running"] is True
        assert response2.json()["maintenance"]["is_running"] is True

        # Cleanup
        maintenance_state["is_running"] = False


class TestDatabaseClearCycle:
    """Test database clearing functionality"""

    def test_clear_database_removes_all_articles(self, test_db, sample_articles):
        """Test that clear_database removes all articles"""
        TestingSessionLocal, _, _ = test_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            # Verify articles exist
            initial_count = db.query(Article).count()
            assert initial_count == 2

            # Create worker and clear database
            worker = NewsWorker()
            worker.clear_database()

            # Verify articles are removed
            db.expire_all()
            final_count = db.query(Article).count()
            assert final_count == 0

            db.close()

    def test_clear_database_also_clears_processed_urls(self, test_db):
        """Test that clear_database clears the processed_urls set"""
        TestingSessionLocal, _, _ = test_db

        with mock_get_connection(TestingSessionLocal):
            worker = NewsWorker()
            worker.processed_urls.add("https://example.com/test")
            worker.processed_urls.add("https://example.com/test2")

            assert len(worker.processed_urls) == 2

            worker.clear_database()

            assert len(worker.processed_urls) == 0


class TestRefreshCycleIntegration:
    """Integration tests for the full refresh cycle"""

    @pytest.mark.asyncio
    async def test_single_fetch_stores_articles(self, test_db):
        """Test that run_single_fetch stores articles in database"""
        TestingSessionLocal, _, _ = test_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            initial_count = db.query(Article).count()
            assert initial_count == 0

            # Run fetch with stub articles (no LLM for speed)
            worker = NewsWorker(limit=2)
            count = await worker.run_single_fetch(use_stub=True, run_llm=False)

            db.expire_all()
            final_count = db.query(Article).count()
            assert final_count > 0
            assert count == final_count

            db.close()

    @pytest.mark.asyncio
    async def test_full_refresh_cycle_simulation(self, test_db, sample_articles):
        """Test simulating a full refresh cycle (clear + fetch)"""
        TestingSessionLocal, _, _ = test_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            # Verify initial state
            initial_count = db.query(Article).count()
            assert initial_count == 2

            # Simulate refresh cycle
            worker = NewsWorker(limit=2)

            # Step 1: Clear database (like 12-hour cycle does)
            worker.clear_database()

            db.expire_all()
            after_clear_count = db.query(Article).count()
            assert after_clear_count == 0

            # Step 2: Fetch new articles
            count = await worker.run_single_fetch(use_stub=True, run_llm=False)

            db.expire_all()
            after_fetch_count = db.query(Article).count()
            assert after_fetch_count > 0
            assert count == after_fetch_count

            db.close()

    @pytest.mark.asyncio
    async def test_maintenance_state_during_fetch(self, test_db):
        """Test that maintenance state reflects fetch status"""
        TestingSessionLocal, _, _ = test_db

        # Reset state
        maintenance_state["is_running"] = False

        with mock_get_connection(TestingSessionLocal):
            # Simulate what the worker loop does
            maintenance_state["is_running"] = True
            maintenance_state["started_at"] = datetime.now(UTC).isoformat()

            assert maintenance_state["is_running"] is True

            # Simulate fetch completion
            worker = NewsWorker(limit=1)
            await worker.run_single_fetch(use_stub=True, run_llm=False)

            maintenance_state["is_running"] = False
            maintenance_state["last_completed"] = datetime.now(UTC).isoformat()

            assert maintenance_state["is_running"] is False
            assert maintenance_state["last_completed"] is not None


class TestWorkerArticleProcessing:
    """Test article processing functionality"""

    def test_is_duplicate_detects_database_duplicates(self, test_db, sample_articles):
        """Test that is_duplicate correctly identifies existing articles"""
        TestingSessionLocal, _, _ = test_db
        db = TestingSessionLocal()

        worker = NewsWorker()

        # Existing URL should be detected as duplicate
        existing_article = {"url": "https://example.com/test1", "title": "Test"}
        assert worker.is_duplicate(db, existing_article) is True

        # New URL should not be duplicate
        new_article = {"url": "https://example.com/new-article", "title": "New"}
        assert worker.is_duplicate(db, new_article) is False

        db.close()

    def test_is_duplicate_checks_memory_cache(self, test_db):
        """Test that is_duplicate checks the processed_urls set"""
        TestingSessionLocal, _, _ = test_db
        db = TestingSessionLocal()

        worker = NewsWorker()
        worker.processed_urls.add("https://example.com/cached")

        cached_article = {"url": "https://example.com/cached", "title": "Cached"}
        assert worker.is_duplicate(db, cached_article) is True

        db.close()

    def test_store_article_returns_article_id(self, test_db):
        """Test that store_article returns the new article ID"""
        TestingSessionLocal, _, _ = test_db
        db = TestingSessionLocal()

        worker = NewsWorker()
        article = {
            "title": "New Test Article",
            "source": "TestSource",
            "url": "https://example.com/new-test",
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        article_id = worker.store_article(db, article)

        assert article_id is not None
        assert isinstance(article_id, int)
        assert article_id > 0

        # Verify article exists in database
        stored = db.query(Article).filter(Article.article_id == article_id).first()
        assert stored is not None
        assert stored.title == "New Test Article"

        db.close()


class TestRefreshCycleWithRealRSS:
    """Integration tests with real RSS feeds (requires network)"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_NETWORK_TESTS", "true").lower() == "true",
        reason="Skipping network tests"
    )
    async def test_rss_fetch_returns_articles(self, test_db):
        """Test that RSS fetch returns actual articles"""
        worker = NewsWorker(limit=2)
        articles = await worker.fetch_rss_articles()

        assert isinstance(articles, list)
        # Should get some articles if network is available
        if articles:
            assert "title" in articles[0]
            assert "source" in articles[0]
            assert "url" in articles[0]


class TestManualRefreshTrigger:
    """Helper tests for manually triggering a refresh cycle"""

    @pytest.mark.asyncio
    async def test_manual_refresh_cycle(self, test_db):
        """
        Manual test to simulate a full 12-hour refresh cycle.

        This test can be run to verify the full cycle works:
        1. Sets maintenance mode to running
        2. Clears database
        3. Fetches new articles (stubbed)
        4. Sets maintenance mode to complete

        Run with: pytest tests/test_maintenance_cycle.py::TestManualRefreshTrigger -v
        """
        TestingSessionLocal, _, _ = test_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            # ===== PHASE 1: Start maintenance =====
            maintenance_state["is_running"] = True
            maintenance_state["started_at"] = datetime.now(UTC).isoformat()
            assert maintenance_state["is_running"] is True

            # ===== PHASE 2: Clear old data =====
            worker = NewsWorker(limit=3)
            worker.clear_database()

            db.expire_all()
            assert db.query(Article).count() == 0

            # ===== PHASE 3: Fetch new articles =====
            count = await worker.run_single_fetch(use_stub=True, run_llm=False)
            assert count > 0

            db.expire_all()
            assert db.query(Article).count() == count

            # ===== PHASE 4: Complete maintenance =====
            maintenance_state["is_running"] = False
            maintenance_state["last_completed"] = datetime.now(UTC).isoformat()
            maintenance_state["next_refresh"] = datetime.now(UTC).isoformat()

            assert maintenance_state["is_running"] is False
            assert maintenance_state["last_completed"] is not None

            db.close()


class TestEndToEndWithAPI:
    """End-to-end tests using the API client"""

    def test_status_shows_maintenance_mode(self, client):
        """Test that /status correctly reflects maintenance state"""
        # Set maintenance ON
        maintenance_state["is_running"] = True
        maintenance_state["started_at"] = datetime.now(UTC).isoformat()

        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["maintenance"]["is_running"] is True

        # Set maintenance OFF
        maintenance_state["is_running"] = False
        maintenance_state["last_completed"] = datetime.now(UTC).isoformat()

        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["maintenance"]["is_running"] is False

    def test_articles_endpoint_during_maintenance(self, client, sample_articles):
        """Test that articles endpoint still works during maintenance"""
        maintenance_state["is_running"] = True

        # Articles should still be available even during maintenance
        # (frontend decides whether to show them)
        response = client.get("/articles/latest")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data

        maintenance_state["is_running"] = False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
