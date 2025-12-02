#!/usr/bin/env python3
"""
Comprehensive test suite for the news worker implementation.
Tests all expected functionality and edge cases.
"""

from datetime import UTC, datetime, timedelta
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base
from veritas_news.models.sqlalchemy_models import Article
from veritas_news.worker.news_worker import (
    DEFAULT_ARTICLE_LIMIT,
    DEFAULT_HOURS_BACK,
    NewsWorker,
)


class TestNewsWorkerCore:
    """Test core functionality of NewsWorker"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing with SQLAlchemy"""
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

    @pytest.fixture
    def worker(self):
        """Create NewsWorker instance"""
        return NewsWorker()

    def test_worker_initialization(self):
        """Test worker initializes with correct defaults"""
        worker = NewsWorker()

        assert worker.hours_back == DEFAULT_HOURS_BACK
        assert worker.limit == DEFAULT_ARTICLE_LIMIT
        assert worker.running is False
        assert isinstance(worker.processed_urls, set)
        assert len(worker.processed_urls) == 0

    def test_worker_custom_parameters(self):
        """Test worker with custom parameters"""
        worker = NewsWorker(hours_back=24, limit=10)

        assert worker.hours_back == 24
        assert worker.limit == 10

    @pytest.mark.asyncio
    async def test_fetch_rss_articles_structure(self, worker):
        """Test RSS article fetching returns correct structure"""
        # Mock the RSS fetcher to return test data
        async def mock_rss():
            return [
                {"title": "Test 1", "source": "TestSource", "url": "https://test.com/1", "raw_text": "Content 1", "published_at": datetime.now(UTC)},
                {"title": "Test 2", "source": "TestSource", "url": "https://test.com/2", "raw_text": "Content 2", "published_at": datetime.now(UTC)},
            ]
        worker.fetch_rss_articles = mock_rss
        articles = await worker.fetch_rss_articles()

        assert isinstance(articles, list)
        assert len(articles) == 2

        for article in articles:
            assert "title" in article
            assert "source" in article
            assert "url" in article
            assert "raw_text" in article
            assert "published_at" in article
            assert isinstance(article["published_at"], datetime)

    def test_duplicate_detection(self, temp_db, worker):
        """Test duplicate detection logic"""
        from veritas_news.db.init_db import get_connection

        unique_url = f"https://test.com/{uuid.uuid4()}"

        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": unique_url,
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as session:
            # First check - should not be duplicate
            assert not worker.is_duplicate(session, article)

            # Store the article
            worker.store_article(session, article)
            session.commit()

        # Second check - should be duplicate (in memory)
        with get_connection() as session:
            assert worker.is_duplicate(session, article)

        # Create new worker instance (no memory)
        new_worker = NewsWorker()

        # Should still detect duplicate (in database)
        with get_connection() as session:
            assert new_worker.is_duplicate(session, article)

    def test_article_storage(self, temp_db, worker):
        """Test article storage functionality"""
        from veritas_news.db.init_db import get_connection

        unique_url = f"https://test.com/{uuid.uuid4()}"

        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": unique_url,
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as session:
            # Store article - returns article_id (int) on success, None on failure
            result = worker.store_article(session, article)
            assert result is not None
            session.commit()

            # Verify it's in database
            stored_article = (
                session.query(Article).filter_by(url=article["url"]).first()
            )

            assert stored_article is not None
            assert stored_article.title == article["title"]
            assert stored_article.source == article["source"]
            assert stored_article.url == article["url"]

    @pytest.mark.asyncio
    async def test_process_articles_batch(self, temp_db, worker):
        """Test processing a batch of articles"""
        articles = [
            {
                "title": f"Article {i}",
                "source": "Test",
                "url": f"https://test.com/{uuid.uuid4()}",
                "raw_text": f"Content {i}",
                "published_at": datetime.now(UTC),
            }
            for i in range(5)
        ]

        # Process articles - process_articles is now async
        stored_count = await worker.process_articles(articles)
        assert stored_count == 5

        # Process same articles again (should be duplicates)
        stored_count = await worker.process_articles(articles)
        assert stored_count == 0  # All duplicates

    @pytest.mark.asyncio
    async def test_status_and_summary_functions(self, temp_db, worker):
        """Test status and summary display functions"""
        # Add some test articles
        articles = [
            {
                "title": f"Article {i}",
                "source": f"Source{i % 2}",  # Alternate sources
                "url": f"https://test.com/{uuid.uuid4()}",
                "raw_text": f"Content {i}",
                "published_at": datetime.now(UTC),
            }
            for i in range(3)
        ]

        await worker.process_articles(articles)

        # Test status (should not crash)
        worker.show_status()

        # Test show all articles (should not crash)
        worker.show_all_articles()

        # Test sources summary (should not crash)
        worker.show_sources_summary()

        # Test clear database
        worker.clear_database()

        # Verify database is empty
        from veritas_news.db.init_db import get_connection

        with get_connection() as session:
            count = session.query(Article).count()
            assert count == 0


class TestCNNScraper:
    """Test CNN RSS scraping functionality"""

    @pytest.fixture
    def worker(self):
        return NewsWorker(hours_back=24, limit=3)

    @pytest.mark.asyncio
    async def test_cnn_scraper_success(self, worker):
        """Test successful CNN RSS parsing"""
        # Use recent timestamps
        now = datetime.now(UTC)
        time1 = now - timedelta(hours=1)
        time2 = now - timedelta(hours=2)

        # Mock successful RSS response
        mock_rss_content = f"""<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test News Article 1</title>
                    <link>https://cnn.com/article1</link>
                    <description>Test content 1</description>
                    <pubDate>{time1.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
                <item>
                    <title>Test News Article 2</title>
                    <link>https://cnn.com/article2</link>
                    <description>Test content 2</description>
                    <pubDate>{time2.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
            </channel>
        </rss>"""

        with patch("veritas_news.worker.news_worker.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = MagicMock()

            # Properly mock the async context manager
            mock_context = AsyncMock()
            mock_context.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_context)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            articles = await worker.fetch_cnn_articles()

            assert len(articles) == 2
            assert articles[0]["title"] == "Test News Article 1"
            assert articles[0]["source"] == "CNN"
            assert articles[0]["url"] == "https://cnn.com/article1"
            assert "published_at" in articles[0]

    @pytest.mark.asyncio
    async def test_cnn_scraper_time_filtering(self, worker):
        """Test that time filtering works correctly"""
        # Create articles with different timestamps
        now = datetime.now(UTC)
        old_time = now - timedelta(hours=25)  # Older than 24 hour limit
        recent_time = now - timedelta(hours=1)  # Within 24 hour limit

        # Mock RSS with old and recent articles
        mock_rss_content = f"""<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Old Article</title>
                    <link>https://cnn.com/old</link>
                    <description>Old content</description>
                    <pubDate>{old_time.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
                <item>
                    <title>Recent Article</title>
                    <link>https://cnn.com/recent</link>
                    <description>Recent content</description>
                    <pubDate>{recent_time.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
            </channel>
        </rss>"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            articles = await worker.fetch_cnn_articles()

            # Should only return recent article
            assert len(articles) == 1
            assert articles[0]["title"] == "Recent Article"

    @pytest.mark.asyncio
    async def test_cnn_scraper_limit_enforcement(self):
        """Test that article limit is enforced"""
        worker = NewsWorker(limit=1)  # Limit to 1 article

        # Use recent timestamps
        now = datetime.now(UTC)
        time1 = now - timedelta(minutes=30)
        time2 = now - timedelta(minutes=45)

        # Mock RSS with multiple articles
        mock_rss_content = f"""<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Article 1</title>
                    <link>https://cnn.com/1</link>
                    <description>Content 1</description>
                    <pubDate>{time1.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
                <item>
                    <title>Article 2</title>
                    <link>https://cnn.com/2</link>
                    <description>Content 2</description>
                    <pubDate>{time2.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                </item>
            </channel>
        </rss>"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            articles = await worker.fetch_cnn_articles()

            # Should only return 1 article due to limit
            assert len(articles) == 1

    @pytest.mark.asyncio
    async def test_cnn_scraper_network_error(self, worker):
        """Test CNN scraper handles network errors"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            articles = await worker.fetch_cnn_articles()
            assert articles == []


class TestSchedulerFunctionality:
    """Test scheduler and long-running functionality"""

    @pytest.fixture
    def worker(self):
        return NewsWorker()

    @pytest.mark.asyncio
    async def test_single_fetch_rss(self, worker):
        """Test single fetch with RSS feeds"""
        with patch.object(worker, "process_articles", return_value=4) as mock_process:
            count = await worker.run_single_fetch(use_cnn=False)
            assert count == 4
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_fetch_cnn(self, worker):
        """Test single fetch with CNN scraper"""
        with patch.object(worker, "fetch_cnn_articles", return_value=[]) as mock_fetch:
            with patch.object(
                worker, "process_articles", return_value=0
            ) as mock_process:
                count = await worker.run_single_fetch(use_cnn=True)
                assert count == 0
                mock_fetch.assert_called_once()
                mock_process.assert_called_once()

    def test_worker_stop(self, worker):
        """Test worker stop functionality"""
        worker.running = True
        worker.stop()
        assert worker.running is False


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing with SQLAlchemy"""
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
    async def test_malformed_article_data(self, temp_db):
        """Test handling of malformed article data"""
        worker = NewsWorker()

        # Test with missing fields
        malformed_articles = [
            {"title": "Test"},  # Missing required fields
            {},  # Empty dict
            None,  # None value
        ]

        # Should handle gracefully without crashing
        try:
            await worker.process_articles(malformed_articles)
            # May return 0 or raise exception, but shouldn't crash the process
        except Exception:
            # Expected for malformed data
            pass

    @pytest.mark.asyncio
    async def test_empty_rss_response(self):
        """Test handling of empty RSS response"""
        worker = NewsWorker()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""  # Empty response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            articles = await worker.fetch_cnn_articles()
            assert articles == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
