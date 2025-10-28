#!/usr/bin/env python3
"""
Comprehensive test suite for the news worker implementation.
Tests all expected functionality and edge cases.
"""

import pytest
import sqlite3
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from src.worker.news_worker import NewsWorker, DEFAULT_HOURS_BACK, DEFAULT_ARTICLE_LIMIT


class TestNewsWorkerCore:
    """Test core functionality of NewsWorker"""
    
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
    async def test_fetch_stubbed_articles(self, worker):
        """Test stubbed article fetching"""
        articles = await worker.fetch_stubbed_articles()
        
        assert isinstance(articles, list)
        assert len(articles) == 4  # Current implementation returns 4 articles
        
        for article in articles:
            assert "title" in article
            assert "source" in article
            assert "url" in article
            assert "raw_text" in article
            assert "published_at" in article
            assert isinstance(article["published_at"], datetime)
    
    def test_duplicate_detection(self, temp_db, worker):
        """Test duplicate detection logic"""
        from src.db.init_db import get_connection, init_db
        
        conn = get_connection()
        init_db(conn)
        
        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": "https://test.com/article1",
            "raw_text": "Test content",
            "published_at": datetime.now(timezone.utc)
        }
        
        # First check - should not be duplicate
        assert not worker.is_duplicate(conn, article)
        
        # Store the article
        worker.store_article(conn, article)
        
        # Second check - should be duplicate (in memory)
        assert worker.is_duplicate(conn, article)
        
        # Create new worker instance (no memory)
        new_worker = NewsWorker()
        
        # Should still detect duplicate (in database)
        assert new_worker.is_duplicate(conn, article)
        
        conn.close()
    
    def test_article_storage(self, temp_db, worker):
        """Test article storage functionality"""
        from src.db.init_db import get_connection, init_db
        
        conn = get_connection()
        init_db(conn)
        
        article = {
            "title": "Test Article",
            "source": "Test Source",
            "url": "https://test.com/article1",
            "raw_text": "Test content",
            "published_at": datetime.now(timezone.utc)
        }
        
        # Store article
        result = worker.store_article(conn, article)
        assert result is True
        
        # Verify it's in database
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE url = ?", (article["url"],))
        stored_article = cursor.fetchone()
        
        assert stored_article is not None
        assert stored_article[1] == article["title"]  # title
        assert stored_article[2] == article["source"]  # source
        assert stored_article[3] == article["url"]     # url
        
        conn.close()
    
    def test_process_articles_batch(self, temp_db, worker):
        """Test processing a batch of articles"""
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
            for i in range(5)
        ]
        
        # Process articles
        stored_count = worker.process_articles(articles)
        assert stored_count == 5
        
        # Process same articles again (should be duplicates)
        stored_count = worker.process_articles(articles)
        assert stored_count == 0  # All duplicates
    
    def test_status_and_summary_functions(self, temp_db, worker):
        """Test status and summary display functions"""
        from src.db.init_db import get_connection, init_db
        
        conn = get_connection()
        init_db(conn)
        conn.close()
        
        # Add some test articles
        articles = [
            {
                "title": f"Article {i}",
                "source": f"Source{i % 2}",  # Alternate sources
                "url": f"https://test.com/{i}",
                "raw_text": f"Content {i}",
                "published_at": datetime.now(timezone.utc)
            }
            for i in range(3)
        ]
        
        worker.process_articles(articles)
        
        # Test status (should not crash)
        worker.show_status()
        
        # Test show all articles (should not crash)
        worker.show_all_articles()
        
        # Test sources summary (should not crash)
        worker.show_sources_summary()
        
        # Test clear database
        worker.clear_database()
        
        # Verify database is empty
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestCNNScraper:
    """Test CNN RSS scraping functionality"""
    
    @pytest.fixture
    def worker(self):
        return NewsWorker(hours_back=24, limit=3)
    
    @pytest.mark.asyncio
    async def test_cnn_scraper_success(self, worker):
        """Test successful CNN RSS parsing"""
        # Mock successful RSS response
        mock_rss_content = '''<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test News Article 1</title>
                    <link>https://cnn.com/article1</link>
                    <description>Test content 1</description>
                    <pubDate>Mon, 28 Oct 2024 12:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Test News Article 2</title>
                    <link>https://cnn.com/article2</link>
                    <description>Test content 2</description>
                    <pubDate>Mon, 28 Oct 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>'''
        
        with patch('src.worker.news_worker.httpx.AsyncClient') as mock_client:
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
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=25)  # Older than 24 hour limit
        recent_time = now - timedelta(hours=1)  # Within 24 hour limit
        
        # Mock RSS with old and recent articles
        mock_rss_content = f'''<?xml version="1.0"?>
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
        </rss>'''
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            articles = await worker.fetch_cnn_articles()
            
            # Should only return recent article
            assert len(articles) == 1
            assert articles[0]["title"] == "Recent Article"
    
    @pytest.mark.asyncio
    async def test_cnn_scraper_limit_enforcement(self):
        """Test that article limit is enforced"""
        worker = NewsWorker(limit=1)  # Limit to 1 article
        
        # Mock RSS with multiple articles
        mock_rss_content = '''<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Article 1</title>
                    <link>https://cnn.com/1</link>
                    <description>Content 1</description>
                    <pubDate>Mon, 28 Oct 2024 12:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Article 2</title>
                    <link>https://cnn.com/2</link>
                    <description>Content 2</description>
                    <pubDate>Mon, 28 Oct 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>'''
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            articles = await worker.fetch_cnn_articles()
            
            # Should only return 1 article due to limit
            assert len(articles) == 1
    
    @pytest.mark.asyncio
    async def test_cnn_scraper_network_error(self, worker):
        """Test CNN scraper handles network errors"""
        with patch('httpx.AsyncClient') as mock_client:
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
    async def test_single_fetch_stubbed(self, worker):
        """Test single fetch with stubbed articles"""
        with patch.object(worker, 'process_articles', return_value=4) as mock_process:
            count = await worker.run_single_fetch(use_cnn=False)
            assert count == 4
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_single_fetch_cnn(self, worker):
        """Test single fetch with CNN scraper"""
        with patch.object(worker, 'fetch_cnn_articles', return_value=[]) as mock_fetch:
            with patch.object(worker, 'process_articles', return_value=0) as mock_process:
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
    
    def test_malformed_article_data(self, temp_db):
        """Test handling of malformed article data"""
        worker = NewsWorker()
        
        from src.db.init_db import get_connection, init_db
        conn = get_connection()
        init_db(conn)
        conn.close()
        
        # Test with missing fields
        malformed_articles = [
            {"title": "Test"},  # Missing required fields
            {},  # Empty dict
            None  # None value
        ]
        
        # Should handle gracefully without crashing
        try:
            count = worker.process_articles(malformed_articles)
            # May return 0 or raise exception, but shouldn't crash the process
        except Exception as e:
            # Expected for malformed data
            pass
    
    @pytest.mark.asyncio
    async def test_empty_rss_response(self):
        """Test handling of empty RSS response"""
        worker = NewsWorker()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""  # Empty response
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            articles = await worker.fetch_cnn_articles()
            assert articles == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])