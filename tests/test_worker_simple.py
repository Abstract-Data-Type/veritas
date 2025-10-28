#!/usr/bin/env python3
"""
Simple, focused tests for the news worker - no network calls, no complex async.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.worker.news_worker import NewsWorker


class TestWorkerBasics:
    """Basic functionality tests - no network, no complex async"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        old_db_path = os.environ.get('DB_PATH')
        os.environ['DB_PATH'] = path
        
        yield path
        
        os.unlink(path)
        if old_db_path:
            os.environ['DB_PATH'] = old_db_path
        elif 'DB_PATH' in os.environ:
            del os.environ['DB_PATH']
    
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
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        # Article with None published_at - this was the bug
        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": "https://test.com/1",
            "raw_text": "Test content",
            "published_at": None  # This should not crash anymore
        }
        
        # Should succeed now
        result = worker.store_article(conn, article)
        assert result is True
        
        # Verify it was stored
        cursor = conn.cursor()
        cursor.execute("SELECT title, published_at FROM articles WHERE url = ?", (article["url"],))
        stored = cursor.fetchone()
        
        assert stored is not None
        assert stored[0] == "Test Article"
        assert stored[1] is not None  # Should have fallback timestamp
        
        conn.close()
    
    def test_duplicate_detection(self, temp_db):
        """Test duplicate detection works"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        article = {
            "title": "Test Article",
            "source": "Test Source", 
            "url": "https://test.com/1",
            "raw_text": "Test content",
            "published_at": datetime.now(timezone.utc)
        }
        
        # First check - not duplicate
        assert not worker.is_duplicate(conn, article)
        
        # Store it
        worker.store_article(conn, article)
        
        # Second check - should be duplicate
        assert worker.is_duplicate(conn, article)
        
        conn.close()
    
    def test_article_storage_basic(self, temp_db):
        """Test basic article storage"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": "https://test.com/1", 
            "raw_text": "Test content",
            "published_at": datetime.now(timezone.utc)
        }
        
        result = worker.store_article(conn, article)
        assert result is True
        
        # Verify in database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        assert count == 1
        
        conn.close()
    
    def test_process_articles_batch(self, temp_db):
        """Test processing multiple articles"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        conn.close()
        
        articles = [
            {
                "title": f"Article {i}",
                "source": "Test",
                "url": f"https://test.com/{i}",
                "raw_text": f"Content {i}",
                "published_at": datetime.now(timezone.utc)
            }
            for i in range(3)
        ]
        
        # Process articles
        stored_count = worker.process_articles(articles)
        assert stored_count == 3
        
        # Process same articles again - should be duplicates
        stored_count = worker.process_articles(articles)
        assert stored_count == 0
    
    def test_empty_fields_handling(self, temp_db):
        """Test handling of empty article fields"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        # Article with empty fields
        article = {
            "title": "",
            "source": "",
            "url": "https://test.com/empty",
            "raw_text": "",
            "published_at": datetime.now(timezone.utc)
        }
        
        # Should still store (current implementation doesn't validate)
        result = worker.store_article(conn, article)
        assert result is True
        
        conn.close()
    
    def test_worker_status_functions(self, temp_db):
        """Test status functions don't crash"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        conn.close()
        
        # These should not crash even with empty database
        worker.show_status()
        worker.show_all_articles()
        worker.show_sources_summary()
        
        # Clear should work
        worker.clear_database()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])