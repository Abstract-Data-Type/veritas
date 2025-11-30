#!/usr/bin/env python3
"""
Simple, focused tests for the news worker - no network calls, no complex async.
"""

from datetime import UTC, datetime
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.models.sqlalchemy_models import Article
from veritas_news.worker.news_worker import NewsWorker


class TestWorkerBasics:
    """Basic functionality tests - no network, no complex async"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        old_db_path = os.environ.get("DB_PATH")
        old_db_url = os.environ.get("SQLALCHEMY_DATABASE_URL")

        # Set unique DB path for this test
        os.environ["DB_PATH"] = path
        os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{path}"

        # Force reload of the engine to use new database

        from veritas_news.db import sqlalchemy

        sqlalchemy.engine = create_engine(
            f"sqlite:///{path}", connect_args={"check_same_thread": False}
        )
        sqlalchemy.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=sqlalchemy.engine
        )

        # Initialize the database with SQLAlchemy
        from veritas_news.db.init_db import init_db

        init_db()

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

        # Restore environment
        if old_db_path:
            os.environ["DB_PATH"] = old_db_path
        elif "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]

        if old_db_url:
            os.environ["SQLALCHEMY_DATABASE_URL"] = old_db_url
        elif "SQLALCHEMY_DATABASE_URL" in os.environ:
            del os.environ["SQLALCHEMY_DATABASE_URL"]

        # Restore original engine
        sqlalchemy.engine = create_engine(
            os.getenv(
                "SQLALCHEMY_DATABASE_URL",
                f"sqlite:///{os.getenv('DB_PATH', 'veritas_news.db')}",
            ),
            connect_args={"check_same_thread": False},
        )
        sqlalchemy.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=sqlalchemy.engine
        )

    def test_worker_initialization(self):
        """Test worker initializes correctly"""
        worker = NewsWorker()
        assert worker.hours_back == 1
        assert worker.limit == 5
        assert worker.running is False
        assert len(worker.processed_urls) == 0

        # Custom params
        worker2 = NewsWorker(hours_back=24, limit=10)
        assert worker2.hours_back == 24
        assert worker2.limit == 10

    def test_datetime_bug_fix(self, temp_db):
        """Test the main bug fix - None published_at should not crash"""
        worker = NewsWorker()

        import uuid

        from veritas_news.db.init_db import get_connection

        # Article with None published_at - this was the bug
        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": f"https://test.com/datetime-{uuid.uuid4()}",
            "raw_text": "Test content",
            "published_at": None,  # This should not crash anymore
        }

        # Should succeed now - returns article_id (int) on success
        with get_connection() as db:
            result = worker.store_article(db, article)
            assert result is not None

            # Verify it was stored
            stored = db.query(Article).filter(Article.url == article["url"]).first()

            assert stored is not None
            assert stored.title == "Test Article"
            assert stored.published_at is not None  # Should have fallback timestamp

    def test_duplicate_detection(self, temp_db):
        """Test duplicate detection works"""
        worker = NewsWorker()

        import uuid

        from veritas_news.db.init_db import get_connection

        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": f"https://test.com/duplicate-{uuid.uuid4()}",
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as db:
            # First check - not duplicate
            assert not worker.is_duplicate(db, article)

            # Store it
            worker.store_article(db, article)

            # Second check - should be duplicate
            assert worker.is_duplicate(db, article)

    def test_article_storage_basic(self, temp_db):
        """Test basic article storage"""
        worker = NewsWorker()

        import uuid

        from veritas_news.db.init_db import get_connection

        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": f"https://test.com/storage-{uuid.uuid4()}",
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as db:
            result = worker.store_article(db, article)
            # store_article returns article_id (int) on success, None on failure
            assert result is not None

            # Verify in database
            count = db.query(Article).count()
            assert count >= 1  # At least our article is there

    @pytest.mark.asyncio
    async def test_process_articles_batch(self, temp_db):
        """Test processing multiple articles"""
        worker = NewsWorker()

        import uuid

        batch_id = uuid.uuid4()

        articles = [
            {
                "title": f"Article {i}",
                "source": "Test",
                "url": f"https://test.com/batch-{batch_id}-{i}",
                "raw_text": f"Content {i}",
                "published_at": datetime.now(UTC),
            }
            for i in range(3)
        ]

        # Process articles - process_articles is now async
        stored_count = await worker.process_articles(articles)
        assert stored_count == 3

        # Process same articles again - should be duplicates
        stored_count = await worker.process_articles(articles)
        assert stored_count == 0

    def test_empty_fields_handling(self, temp_db):
        """Test handling of empty article fields"""
        worker = NewsWorker()

        import uuid

        from veritas_news.db.init_db import get_connection

        # Article with empty fields
        article = {
            "title": "",
            "source": "",
            "url": f"https://test.com/empty-{uuid.uuid4()}",
            "raw_text": "",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as db:
            # Should still store (current implementation doesn't validate)
            # Returns article_id (int) on success
            result = worker.store_article(db, article)
            assert result is not None

    def test_worker_status_functions(self, temp_db):
        """Test status functions don't crash"""
        worker = NewsWorker()

        # These should not crash even with empty database
        worker.show_status()
        worker.show_all_articles()
        worker.show_sources_summary()

        # Clear should work
        worker.clear_database()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
