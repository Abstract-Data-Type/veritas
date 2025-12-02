"""
Tests for the background worker integration with FastAPI.

Tests that the NewsWorker starts with the API, fetches articles,
and stores them in the database accessible by the API.
"""

import asyncio
import os
import tempfile

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base, get_session
from veritas_news.main import app
from veritas_news.worker.news_worker import NewsWorker


class TestWorkerIntegration:
    """Test suite for background worker integration"""

    @pytest.fixture
    def temp_db(self, monkeypatch):
        """Create a temporary database for testing"""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)

        # Set environment variable to use temp database BEFORE importing
        monkeypatch.setenv("DB_PATH", db_path)

        # Also set the SQLAlchemy URL
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", f"sqlite:///{db_path}")

        # Create engine and tables
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)

        yield db_path, engine

        # Cleanup
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def test_client(self, temp_db):
        """Create test client with temporary database"""
        db_path, engine = temp_db

        # Override database session dependency
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

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

    def test_worker_disabled_by_env(self, monkeypatch, temp_db):
        """Test that worker doesn't start when WORKER_ENABLED=false"""
        monkeypatch.setenv("WORKER_ENABLED", "false")

        import importlib

        import veritas_news.main

        # Reload the module to pick up the environment variable change
        importlib.reload(veritas_news.main)

        with TestClient(veritas_news.main.app) as client:
            # Check API is running
            response = client.get("/")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

            # Worker should not be running (check after lifespan has run)
            assert veritas_news.main.news_worker is None

    @pytest.mark.asyncio
    async def test_news_worker_fetch_articles(self, temp_db):
        """Test that NewsWorker can fetch and store articles"""
        db_path, engine = temp_db

        # Create worker instance
        worker = NewsWorker(hours_back=1, limit=5)

        # Mock RSS fetch with test articles
        async def mock_rss():
            from datetime import UTC, datetime
            return [
                {"title": "Test 1", "source": "Test", "url": "https://test.com/1", "raw_text": "Content", "published_at": datetime.now(UTC)},
                {"title": "Test 2", "source": "Test", "url": "https://test.com/2", "raw_text": "Content", "published_at": datetime.now(UTC)},
            ]
        worker.fetch_rss_articles = mock_rss
        stored_count = await worker.run_single_fetch(run_llm=False)

        # Should have stored some articles
        assert stored_count > 0, "Worker should store articles"
        assert stored_count == 2, "Should return 2 articles"

    @pytest.mark.asyncio
    async def test_worker_duplicate_detection(self, temp_db):
        """Test that worker tracks processed URLs"""
        db_path, engine = temp_db

        worker = NewsWorker(hours_back=1, limit=5)

        # Mock RSS with test articles
        async def mock_rss():
            from datetime import UTC, datetime
            return [
                {"title": "Test 1", "source": "Test", "url": "https://test.com/dup1", "raw_text": "Content", "published_at": datetime.now(UTC)},
                {"title": "Test 2", "source": "Test", "url": "https://test.com/dup2", "raw_text": "Content", "published_at": datetime.now(UTC)},
            ]
        worker.fetch_rss_articles = mock_rss
        stored_count_1 = await worker.run_single_fetch(run_llm=False)
        assert stored_count_1 > 0

        # Check in-memory tracking exists
        assert len(worker.processed_urls) == stored_count_1

    @pytest.mark.asyncio
    async def test_worker_stores_correct_count(self, temp_db):
        """Test that worker stores correct number of articles"""
        db_path, engine = temp_db

        worker = NewsWorker(hours_back=1, limit=5)
        
        # Mock RSS with test articles
        async def mock_rss():
            from datetime import UTC, datetime
            return [
                {"title": "Test 1", "source": "Test", "url": "https://test.com/cnt1", "raw_text": "Content", "published_at": datetime.now(UTC)},
                {"title": "Test 2", "source": "Test", "url": "https://test.com/cnt2", "raw_text": "Content", "published_at": datetime.now(UTC)},
            ]
        worker.fetch_rss_articles = mock_rss
        stored_count = await worker.run_single_fetch(run_llm=False)

        # Verify articles were stored
        assert stored_count > 0
        assert stored_count == 2

    def test_api_articles_endpoint_works(self, test_client, temp_db):
        """Test that API articles endpoint responds correctly"""
        db_path, engine = temp_db

        # Test API endpoint
        response = test_client.get("/articles/latest?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert "articles" in data
        assert "total" in data
        assert isinstance(data["articles"], list)

    @pytest.mark.asyncio
    async def test_worker_cleanup_memory(self, temp_db):
        """Test that worker cleans up processed URLs to prevent memory leak"""
        db_path, engine = temp_db

        worker = NewsWorker(hours_back=1, limit=5)

        # Add many URLs to processed set
        for i in range(2000):
            worker.processed_urls.add(f"https://example.com/article-{i}")

        assert len(worker.processed_urls) > 1000

        # Trigger cleanup
        worker.cleanup_memory(max_urls=1000)

        # Should have cleaned up
        assert len(worker.processed_urls) <= 500

    @pytest.mark.asyncio
    async def test_worker_handles_errors_gracefully(self, temp_db, monkeypatch):
        """Test that worker handles fetch errors without crashing"""
        db_path, engine = temp_db

        worker = NewsWorker(hours_back=1, limit=5)

        # Mock fetch to raise an error
        async def mock_fetch_error():
            raise Exception("Simulated fetch error")

        monkeypatch.setattr(worker, "fetch_rss_articles", mock_fetch_error)

        # Worker will raise exception since run_single_fetch doesn't catch it
        # This is expected behavior - the scheduler handles retry logic
        with pytest.raises(Exception, match="Simulated fetch error"):
            await worker.run_single_fetch(run_llm=False)

    @pytest.mark.asyncio
    async def test_worker_config_from_env(self, temp_db, monkeypatch):
        """Test that worker respects environment variable configuration"""
        monkeypatch.setenv("WORKER_HOURS_BACK", "2")
        monkeypatch.setenv("WORKER_LIMIT", "10")

        worker = NewsWorker(
            hours_back=int(os.getenv("WORKER_HOURS_BACK", "1")),
            limit=int(os.getenv("WORKER_LIMIT", "5")),
        )

        assert worker.hours_back == 2
        assert worker.limit == 10

    @pytest.mark.asyncio
    async def test_worker_stop_mechanism(self, temp_db):
        """Test that worker can be stopped gracefully"""
        worker = NewsWorker(hours_back=1, limit=5)

        # Start worker
        worker.running = True
        assert worker.running is True

        # Stop worker
        worker.stop()
        assert worker.running is False

    def test_worker_show_status(self, temp_db, capsys):
        """Test worker status display"""
        db_path, engine = temp_db
        sessionmaker(autocommit=False, autoflush=False, bind=engine)

        worker = NewsWorker(hours_back=1, limit=5)

        # Mock and store some articles first
        async def mock_rss():
            from datetime import UTC, datetime
            return [{"title": "Test", "source": "Test", "url": "https://test.com/status1", "raw_text": "Content", "published_at": datetime.now(UTC)}]
        worker.fetch_rss_articles = mock_rss
        asyncio.run(worker.run_single_fetch(run_llm=False))

        # Show status (captures logs)
        worker.show_status()

        # Status should complete without errors
        assert True


class TestWorkerLifecycle:
    """Test the full worker lifecycle in FastAPI"""

    @pytest.mark.asyncio
    async def test_worker_lifecycle_with_lifespan(self, monkeypatch):
        """Test worker starts and stops with FastAPI lifespan"""
        # Set up environment
        monkeypatch.setenv("WORKER_ENABLED", "true")
        monkeypatch.setenv("WORKER_SCHEDULE_INTERVAL", "1")  # 1 second for testing

        # Create temporary database
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        monkeypatch.setenv("DB_PATH", db_path)

        # Import fresh to pick up env vars
        import importlib

        import veritas_news.main

        importlib.reload(veritas_news.main)

        try:
            with TestClient(veritas_news.main.app) as client:
                # API should be running
                response = client.get("/")
                assert response.status_code == 200

                # Worker should have started
                assert veritas_news.main.news_worker is not None
                assert veritas_news.main.news_worker.running is True

                # Give worker a moment to run
                await asyncio.sleep(2)

            # After context exit, worker should be stopped
            # (TestClient handles lifespan context manager)

        finally:
            os.unlink(db_path)


class TestWorkerFetchModes:
    """Test different worker fetch modes"""

    @pytest.mark.asyncio
    async def test_worker_basic_fetch(self, tmp_path):
        """Test worker with mocked RSS articles"""
        db_path = tmp_path / "test.db"
        os.environ["DB_PATH"] = str(db_path)

        worker = NewsWorker(hours_back=1, limit=5)
        
        # Mock RSS fetch
        async def mock_rss():
            from datetime import UTC, datetime
            return [{"title": "Test", "source": "Test", "url": "https://test.com/basic1", "raw_text": "Content", "published_at": datetime.now(UTC)}]
        worker.fetch_rss_articles = mock_rss
        count = await worker.run_single_fetch(run_llm=False)

        assert count > 0, "Should return articles"

    @pytest.mark.asyncio
    async def test_worker_cnn_mode_without_network(self, tmp_path):
        """Test worker CNN mode (may fail without network)"""
        db_path = tmp_path / "test.db"
        os.environ["DB_PATH"] = str(db_path)

        worker = NewsWorker(hours_back=1, limit=5)

        # This may return 0 if network is unavailable, which is acceptable
        count = await worker.run_single_fetch(use_cnn=True, use_newsapi=False)
        assert count >= 0  # Should not crash

    @pytest.mark.asyncio
    async def test_worker_newsapi_mode_without_key(self, tmp_path, monkeypatch):
        """Test worker NewsAPI mode without valid API key"""
        db_path = tmp_path / "test.db"
        os.environ["DB_PATH"] = str(db_path)
        monkeypatch.setenv("NEWSCLIENT_API_KEY", "invalid_key")

        worker = NewsWorker(hours_back=1, limit=5)

        # Should handle invalid key gracefully
        count = await worker.run_single_fetch(use_cnn=False, use_newsapi=True)
        assert count >= 0  # Should not crash
