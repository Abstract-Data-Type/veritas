#!/usr/bin/env python3
"""
Unit tests for NewsAPI integration functionality.
"""

from datetime import datetime
import os
import tempfile
from unittest.mock import MagicMock, patch
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base
from veritas_news.models.sqlalchemy_models import Article
from veritas_news.worker.news_worker import NewsWorker


class TestNewsAPIIntegration:
    """Test NewsAPI integration functionality"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Create engine and tables
        engine = create_engine(f"sqlite:///{path}")

        # Enable foreign key constraints
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)

        # Set DB_PATH environment variable
        old_db_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = path

        # Store engine for cleanup
        from veritas_news.db import sqlalchemy as sql_module

        old_engine = sql_module.engine
        sql_module.engine = engine
        sql_module.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

        yield path

        # Cleanup
        sql_module.engine = old_engine
        engine.dispose()
        os.unlink(path)
        if old_db_path:
            os.environ["DB_PATH"] = old_db_path
        elif "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]

    @pytest.mark.asyncio
    async def test_fetch_newsapi_headlines_success(self, temp_db):
        """Test successful NewsAPI headlines fetch"""
        worker = NewsWorker(limit=5)

        # Mock NewsAPI response
        mock_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "Test Article 1",
                    "source": {"name": "CNN"},
                    "url": "https://example.com/article1",
                    "description": "Test description 1",
                    "publishedAt": "2023-12-01T10:30:00Z",
                },
                {
                    "title": "Test Article 2",
                    "source": {"name": "BBC"},
                    "url": "https://example.com/article2",
                    "description": "Test description 2",
                    "publishedAt": "2023-12-01T11:30:00Z",
                },
            ],
        }

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            # Mock environment variable
            mock_getenv.return_value = "test-api-key"

            # Mock NewsAPI client
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            # Fetch articles
            articles = await worker.fetch_newsapi_headlines()

            # Verify results
            assert len(articles) == 2
            assert articles[0]["title"] == "Test Article 1"
            assert articles[0]["source"] == "CNN"
            assert articles[0]["url"] == "https://example.com/article1"
            assert articles[0]["raw_text"] == "Test description 1"
            assert articles[0]["published_at"] is not None

            # Verify API was called correctly
            mock_instance.get_top_headlines.assert_called_once_with(
                country="us", language="en", page_size=5
            )

    @pytest.mark.asyncio
    async def test_fetch_newsapi_no_api_key(self, temp_db):
        """Test NewsAPI fetch without API key"""
        worker = NewsWorker()

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv:
            mock_getenv.return_value = None

            articles = await worker.fetch_newsapi_headlines()

            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_newsapi_api_error(self, temp_db):
        """Test NewsAPI fetch with API error response"""
        worker = NewsWorker()

        mock_response = {"status": "error", "message": "Invalid API key"}

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "invalid-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            articles = await worker.fetch_newsapi_headlines()

            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_newsapi_empty_response(self, temp_db):
        """Test NewsAPI fetch with empty articles"""
        worker = NewsWorker()

        mock_response = {"status": "ok", "totalResults": 0, "articles": []}

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "test-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            articles = await worker.fetch_newsapi_headlines()

            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_newsapi_malformed_article(self, temp_db):
        """Test NewsAPI fetch with malformed article data"""
        worker = NewsWorker()

        mock_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "Good Article",
                    "source": {"name": "CNN"},
                    "url": "https://example.com/good",
                    "description": "Good description",
                    "publishedAt": "2023-12-01T10:30:00Z",
                },
                {
                    # Missing required fields
                    "title": None,
                    "source": None,
                    "url": "",  # Empty URL should be skipped
                    "description": None,
                    "publishedAt": "invalid-date",
                },
            ],
        }

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "test-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            articles = await worker.fetch_newsapi_headlines()

            # Should only return the good article
            assert len(articles) == 1
            assert articles[0]["title"] == "Good Article"

    @pytest.mark.asyncio
    async def test_fetch_newsapi_network_exception(self, temp_db):
        """Test NewsAPI fetch with network exception"""
        worker = NewsWorker()

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "test-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.side_effect = Exception("Network error")
            mock_client.return_value = mock_instance

            articles = await worker.fetch_newsapi_headlines()

            assert articles == []

    def test_newsapi_date_parsing(self, temp_db):
        """Test NewsAPI date parsing edge cases"""
        NewsWorker()

        # Test various date formats
        test_cases = [
            ("2023-12-01T10:30:00Z", True),
            ("2023-12-01T10:30:00.123Z", True),
            ("invalid-date", False),
            (None, False),
            ("", False),
        ]

        for date_str, should_parse in test_cases:

            # Mock the parsing logic
            published_at = None
            if date_str:
                try:
                    published_at = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except:
                    pass

            if should_parse:
                assert published_at is not None
            else:
                assert published_at is None

    def test_newsapi_limit_handling(self, temp_db):
        """Test NewsAPI limit parameter handling"""
        # Test various limits
        test_limits = [1, 5, 50, 100, 150]

        for limit in test_limits:
            worker = NewsWorker(limit=limit)
            expected_api_limit = min(limit, 100)  # API max is 100

            with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
                "veritas_news.worker.news_worker.NewsApiClient"
            ) as mock_client:

                mock_getenv.return_value = "test-api-key"
                mock_instance = MagicMock()
                mock_instance.get_top_headlines.return_value = {
                    "status": "ok",
                    "articles": [],
                }
                mock_client.return_value = mock_instance

                # Create an async wrapper to test
                import asyncio

                asyncio.run(worker.fetch_newsapi_headlines())

                # Verify API was called with correct limit
                mock_instance.get_top_headlines.assert_called_with(
                    country="us", language="en", page_size=expected_api_limit
                )


class TestNewsAPIDatabase:
    """Test NewsAPI database integration"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        engine = create_engine(f"sqlite:///{path}")

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)

        old_db_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = path

        from veritas_news.db import sqlalchemy as sql_module

        old_engine = sql_module.engine
        sql_module.engine = engine
        sql_module.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

        yield path

        sql_module.engine = old_engine
        engine.dispose()
        os.unlink(path)
        if old_db_path:
            os.environ["DB_PATH"] = old_db_path
        elif "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]

    @pytest.mark.asyncio
    async def test_newsapi_database_storage(self, temp_db):
        """Test storing NewsAPI articles in database"""
        worker = NewsWorker(limit=2)

        mock_response = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": "Database Test Article",
                    "source": {"name": "TestNews"},
                    "url": f"https://example.com/test-{uuid.uuid4()}",
                    "description": "Test article for database storage",
                    "publishedAt": "2023-12-01T10:30:00Z",
                }
            ],
        }

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "test-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            # Fetch and store articles
            count = await worker.run_single_fetch(use_newsapi=True)

            assert count == 1

            # Verify in database
            from veritas_news.db.init_db import get_connection

            with get_connection() as session:
                stored = (
                    session.query(Article)
                    .filter_by(title="Database Test Article")
                    .first()
                )

                assert stored is not None
                assert stored.source == "TestNews"
                assert stored.raw_text == "Test article for database storage"

    @pytest.mark.asyncio
    async def test_newsapi_duplicate_detection(self, temp_db):
        """Test duplicate detection for NewsAPI articles"""
        worker = NewsWorker(limit=5)

        test_url = f"https://example.com/duplicate-test-{uuid.uuid4()}"

        mock_response = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": "Duplicate Test Article",
                    "source": {"name": "TestNews"},
                    "url": test_url,
                    "description": "Test duplicate detection",
                    "publishedAt": "2023-12-01T10:30:00Z",
                }
            ],
        }

        with patch("veritas_news.worker.news_worker.os.getenv") as mock_getenv, patch(
            "veritas_news.worker.news_worker.NewsApiClient"
        ) as mock_client:

            mock_getenv.return_value = "test-api-key"
            mock_instance = MagicMock()
            mock_instance.get_top_headlines.return_value = mock_response
            mock_client.return_value = mock_instance

            # First fetch should store the article
            count1 = await worker.run_single_fetch(use_newsapi=True)
            assert count1 == 1

            # Second fetch should detect duplicate
            count2 = await worker.run_single_fetch(use_newsapi=True)
            assert count2 == 0

            # Verify only one article in database
            from veritas_news.db.init_db import get_connection

            with get_connection() as session:
                total = session.query(Article).filter_by(url=test_url).count()
                assert total == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
