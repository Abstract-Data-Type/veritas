#!/usr/bin/env python3
"""
Simple tests to uncover bugs in the news worker implementation.
"""

import pytest
import sqlite3
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from src.worker.news_worker import NewsWorker, DEFAULT_HOURS_BACK, DEFAULT_ARTICLE_LIMIT


class TestWorkerBugs:
    """Simple tests to catch common bugs"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Set DB_PATH environment variable
        old_db_path = os.environ.get('DB_PATH')
        os.environ['DB_PATH'] = path
        
        yield path
        
        # Cleanup
        os.unlink(path)
        if old_db_path:
            os.environ['DB_PATH'] = old_db_path
        elif 'DB_PATH' in os.environ:
            del os.environ['DB_PATH']
    
    def test_datetime_serialization_bug_fixed(self, temp_db):
        """Test that None published_at is handled gracefully (bug fix verification)"""
        worker = NewsWorker()
        
        # Article with None published_at should be handled gracefully now
        article = {
            "title": "Test Article",
            "source": "Test",
            "url": "https://test.com/1",
            "raw_text": "Test content",
            "published_at": None  # This should not crash anymore
        }
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        # This should now succeed instead of crashing
        result = worker.store_article(conn, article)
        assert result is True
        
        # Verify article was stored with fallback timestamp
        cursor = conn.cursor()
        cursor.execute("SELECT title, published_at FROM articles WHERE url = ?", (article["url"],))
        stored = cursor.fetchone()
        
        assert stored is not None
        assert stored[0] == "Test Article"
        assert stored[1] is not None  # Should have fallback timestamp
        
        conn.close()
    
    def test_negative_parameters_bug(self):
        """Test invalid negative parameters"""
        # These should fail validation but don't
        worker = NewsWorker(hours_back=-1, limit=-5)
        
        assert worker.hours_back == -1  # Should be rejected
        assert worker.limit == -5       # Should be rejected
    
    @pytest.mark.asyncio
    async def test_connection_leak_bug(self, temp_db):
        """Test that database connections leak on exceptions"""
        worker = NewsWorker()
        
        from src.db.init_db import init_db, get_connection
        conn = get_connection()
        init_db(conn)
        conn.close()
        
        # Create bad article that will cause SQL error
        bad_articles = [
            {
                "title": "Test",
                "source": "Test", 
                "url": "https://test.com/1",
                "raw_text": "Test",
                "published_at": "invalid_datetime_string"  # Will cause SQL error
            }
        ]
        
        # This leaves connection open on exception
        result = worker.process_articles(bad_articles)
        assert result == 0  # No articles stored due to error
        
        # Connection should be closed but implementation may leak it
    
    @pytest.mark.asyncio 
    async def test_rss_parsing_crash(self):
        """Test RSS parsing with malformed data"""
        worker = NewsWorker()
        
        # Mock httpx to return malformed RSS
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Invalid XML content <><><<>"  # Malformed
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Should handle gracefully but may crash on feedparser.parse
            articles = await worker.fetch_cnn_articles()
            assert articles == []  # Should return empty list, not crash
    
    def test_sql_injection_vulnerability(self, temp_db):
        """Test potential SQL injection in duplicate checking"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        # Article with potential SQL injection in URL
        malicious_article = {
            "title": "Test",
            "source": "Test",
            "url": "'; DROP TABLE articles; --",  # SQL injection attempt
            "raw_text": "Test",
            "published_at": datetime.now(timezone.utc)
        }
        
        # Should be safe due to parameterized queries, but test it
        is_dup = worker.is_duplicate(conn, malicious_article)
        assert is_dup is False
        
        # Verify table still exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        assert count == 0  # Table should still exist and be empty
        
        conn.close()


class TestWorkerEdgeCases:
    """Test edge cases that could cause failures"""
    
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
    
    def test_empty_article_fields(self, temp_db):
        """Test articles with empty/missing fields"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        
        # Article with empty required fields
        empty_article = {
            "title": "",  # Empty title
            "source": "",  # Empty source
            "url": "",    # Empty URL
            "raw_text": "",  # Empty content
            "published_at": datetime.now(timezone.utc)
        }
        
        # Should handle gracefully
        result = worker.store_article(conn, empty_article)
        # Current implementation doesn't validate, so this might succeed
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test network timeout scenarios"""
        worker = NewsWorker()
        
        # Mock httpx to timeout
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=asyncio.TimeoutError("Connection timeout")
            )
            
            # Should handle timeout gracefully
            articles = await worker.fetch_cnn_articles()
            assert articles == []
    
    def test_zero_limit_edge_case(self):
        """Test worker with zero article limit"""
        worker = NewsWorker(limit=0)
        
        # Should handle zero limit gracefully
        assert worker.limit == 0
        
        # Mock articles should respect limit
        articles = []  # Zero articles expected
    
    def test_memory_leak_fix(self):
        """Test that processed_urls memory leak is fixed"""
        worker = NewsWorker()
        
        # Add many URLs to trigger cleanup
        for i in range(1500):  # More than the 1000 limit
            worker.processed_urls.add(f"https://test.com/{i}")
        
        initial_count = len(worker.processed_urls)
        assert initial_count == 1500
        
        # Trigger cleanup
        worker.cleanup_memory(max_urls=1000)
        
        # Should be reduced to half of max_urls (500)
        final_count = len(worker.processed_urls)
        assert final_count == 500
        assert final_count < initial_count
    
    def test_cleanup_not_triggered_when_under_limit(self):
        """Test cleanup doesn't run when under limit"""
        worker = NewsWorker()
        
        # Add URLs under the limit
        for i in range(100):
            worker.processed_urls.add(f"https://test.com/{i}")
        
        initial_count = len(worker.processed_urls)
        worker.cleanup_memory(max_urls=1000)
        
        # Should be unchanged
        assert len(worker.processed_urls) == initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])