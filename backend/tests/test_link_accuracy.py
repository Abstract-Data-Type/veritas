#!/usr/bin/env python3
"""
Test suite to verify URL/link fetching and processing accuracy.

This module tests that:
1. URLs are correctly extracted from sources
2. URLs are properly formatted and valid
3. URLs are stored correctly in the database
4. URLs retrieved match what was stored
5. URLs are accessible (for real sources)
"""

from datetime import UTC, datetime
import os
import re
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base
from veritas_news.models.sqlalchemy_models import Article
from veritas_news.worker.news_worker import NewsWorker


def is_valid_url(url: str) -> bool:
    """
    Validate that a string is a properly formatted URL.

    Args:
        url: String to validate as URL

    Returns:
        True if valid URL format, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        result = urlparse(url)
        # Must have scheme (http/https) and netloc (domain)
        # Allow localhost without dots (e.g., http://localhost:8000)
        has_valid_host = result.netloc and (
            '.' in result.netloc or
            result.netloc.startswith('localhost') or
            result.netloc.split(':')[0] == 'localhost'
        )

        # Check for double slashes in path (common bug)
        path_has_double_slash = '//' in result.path

        return all([
            result.scheme in ('http', 'https'),
            has_valid_host,
            not path_has_double_slash,  # No double slashes in path
        ])
    except Exception:
        return False


def has_valid_domain(url: str) -> bool:
    """
    Check if URL has a valid domain format.

    Args:
        url: URL string to check

    Returns:
        True if domain format is valid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        # Basic domain validation
        if not domain:
            return False

        # Check for valid domain characters
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, domain))
    except Exception:
        return False


class TestURLValidation:
    """Test URL validation utilities"""

    def test_valid_http_url(self):
        """Test that valid HTTP URLs pass validation"""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com/path",
            "https://example.com/path/to/article",
            "https://sub.example.com/article?id=123",
            "https://cnn.com/2024/01/01/article",
            "https://reuters.com/article-abc-def",
        ]

        for url in valid_urls:
            assert is_valid_url(url), f"Expected {url} to be valid"

    def test_invalid_urls(self):
        """Test that invalid URLs fail validation"""
        invalid_urls = [
            "",
            None,
            "not a url",
            "ftp://example.com",  # Wrong scheme
            "http://",  # No domain
            "http://example",  # No TLD
            "//example.com",  # No scheme
            "http://example.com//path",  # Double slash in path
        ]

        for url in invalid_urls:
            assert not is_valid_url(url), f"Expected {url} to be invalid"

    def test_double_slash_detection(self):
        """Test that double slashes in URL paths are detected"""
        # This is a common bug when concatenating URL parts
        bad_url = "http://localhost:8000//summarize"
        assert not is_valid_url(bad_url), "Double slash in path should be invalid"

        good_url = "http://localhost:8000/summarize"
        assert is_valid_url(good_url), "Single slash in path should be valid"


class TestURLStorageAndRetrieval:
    """Test that URLs are stored and retrieved accurately from database"""

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

    def test_url_stored_exactly_as_provided(self, temp_db, worker):
        """Test that URL is stored exactly as provided, not modified"""
        from veritas_news.db.init_db import get_connection

        # Use unique URLs with uuid to avoid collision with other tests
        test_urls = [
            f"https://example.com/article-{uuid.uuid4()}",
            f"https://www.cnn.com/2024/01/01/politics/article-{uuid.uuid4()}/index.html",
            f"https://reuters.com/world/article?id={uuid.uuid4()}&ref=homepage",
            f"https://news.example.com/path/to/very/long/article/{uuid.uuid4()}",
        ]

        for original_url in test_urls:
            article = {
                "title": f"Test Article for {original_url[:30]}",
                "source": "Test",
                "url": original_url,
                "raw_text": "Test content",
                "published_at": datetime.now(UTC),
            }

            with get_connection() as session:
                # Store the article - returns article_id (int) on success
                result = worker.store_article(session, article)
                assert result is not None
                session.commit()

                # Retrieve and verify
                stored = session.query(Article).filter_by(url=original_url).first()

                assert stored is not None, f"Article with URL {original_url} not found"
                assert stored.url == original_url, \
                    f"URL mismatch: stored '{stored.url}' != original '{original_url}'"

    def test_url_with_special_characters(self, temp_db, worker):
        """Test that URLs with special characters are handled correctly"""
        from veritas_news.db.init_db import get_connection

        special_urls = [
            "https://example.com/article?query=test%20value",
            "https://example.com/path/with+plus/article",
            "https://example.com/article#section",
            "https://example.com/article?a=1&b=2&c=3",
        ]

        for original_url in special_urls:
            unique_url = f"{original_url}&uuid={uuid.uuid4()}"

            article = {
                "title": "Test Article",
                "source": "Test",
                "url": unique_url,
                "raw_text": "Test content",
                "published_at": datetime.now(UTC),
            }

            with get_connection() as session:
                result = worker.store_article(session, article)
                # store_article returns article_id (int) on success, None on failure
                assert result is not None
                session.commit()

                stored = session.query(Article).filter_by(url=unique_url).first()
                assert stored is not None
                assert stored.url == unique_url

    def test_url_not_truncated(self, temp_db, worker):
        """Test that long URLs are not truncated during storage"""
        from veritas_news.db.init_db import get_connection

        # Create a very long but valid URL
        long_path = "/".join(["segment"] * 50)
        long_url = f"https://example.com/{long_path}/article-{uuid.uuid4()}"

        article = {
            "title": "Article with Long URL",
            "source": "Test",
            "url": long_url,
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as session:
            result = worker.store_article(session, article)
            # store_article returns article_id (int) on success, None on failure
            assert result is not None
            session.commit()

            stored = session.query(Article).filter_by(url=long_url).first()
            assert stored is not None
            assert len(stored.url) == len(long_url), \
                f"URL was truncated: {len(stored.url)} != {len(long_url)}"
            assert stored.url == long_url


class TestCNNFetcherURLs:
    """Test URL accuracy when fetching from CNN RSS"""

    @pytest.fixture
    def worker(self):
        """Create NewsWorker instance with small limit"""
        return NewsWorker(hours_back=24, limit=5)

    @pytest.mark.asyncio
    async def test_cnn_urls_are_valid_format(self, worker):
        """Test that CNN RSS URLs are in valid format"""
        # Mock the HTTP response to avoid network calls
        mock_rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>CNN Top Stories</title>
                <item>
                    <title>Test Article 1</title>
                    <link>https://www.cnn.com/2024/01/01/politics/test-article-1/index.html</link>
                    <description>Test description 1</description>
                    <pubDate>Sat, 30 Nov 2024 12:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Test Article 2</title>
                    <link>https://www.cnn.com/2024/01/01/world/test-article-2/index.html</link>
                    <description>Test description 2</description>
                    <pubDate>Sat, 30 Nov 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_content
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            articles = await worker.fetch_cnn_articles()

        for article in articles:
            url = article.get("url", "")

            # URL should be valid
            assert is_valid_url(url), f"Invalid URL format: {url}"

            # CNN URLs should start with https://www.cnn.com or https://cnn.com
            parsed = urlparse(url)
            assert parsed.netloc in ("www.cnn.com", "cnn.com"), \
                f"Unexpected CNN domain: {parsed.netloc}"

    @pytest.mark.asyncio
    async def test_cnn_url_not_modified_from_rss(self, worker):
        """Test that CNN URLs are extracted exactly as they appear in RSS"""
        expected_url = "https://www.cnn.com/2024/01/01/exact-url-test/index.html"

        # Use current time to avoid being filtered out by the time cutoff
        from datetime import datetime
        current_time = datetime.now(UTC)
        pub_date = current_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        mock_rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>CNN Top Stories</title>
                <item>
                    <title>Exact URL Test Article</title>
                    <link>{expected_url}</link>
                    <description>Test description</description>
                    <pubDate>{pub_date}</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_content
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            articles = await worker.fetch_cnn_articles()

        assert len(articles) == 1
        assert articles[0]["url"] == expected_url, \
            f"URL was modified: '{articles[0]['url']}' != '{expected_url}'"


class TestNewsAPIURLs:
    """Test URL accuracy when fetching from NewsAPI"""

    @pytest.fixture
    def worker(self):
        """Create NewsWorker instance"""
        return NewsWorker(limit=5)

    @pytest.mark.asyncio
    async def test_newsapi_urls_are_valid_format(self, worker):
        """Test that NewsAPI URLs are in valid format"""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article 1",
                    "source": {"name": "Test Source"},
                    "url": "https://www.testsource.com/article/12345",
                    "description": "Test description",
                    "publishedAt": "2024-11-30T12:00:00Z",
                },
                {
                    "title": "Test Article 2",
                    "source": {"name": "Another Source"},
                    "url": "https://anothersource.com/news/article-name",
                    "description": "Another description",
                    "publishedAt": "2024-11-30T11:00:00Z",
                },
            ],
        }

        with patch.dict(os.environ, {"NEWSCLIENT_API_KEY": "test_key"}):
            with patch("veritas_news.worker.news_worker.NewsApiClient") as mock_newsapi:
                mock_client = MagicMock()
                mock_client.get_top_headlines.return_value = mock_response
                mock_newsapi.return_value = mock_client

                articles = await worker.fetch_newsapi_headlines()

        assert len(articles) == 2

        for article in articles:
            url = article.get("url", "")
            assert is_valid_url(url), f"Invalid URL format: {url}"

    @pytest.mark.asyncio
    async def test_newsapi_empty_url_skipped(self, worker):
        """Test that articles with empty URLs are skipped"""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "title": "Article with URL",
                    "source": {"name": "Test Source"},
                    "url": "https://example.com/article",
                    "description": "Has URL",
                    "publishedAt": "2024-11-30T12:00:00Z",
                },
                {
                    "title": "Article without URL",
                    "source": {"name": "Test Source"},
                    "url": "",  # Empty URL
                    "description": "No URL",
                    "publishedAt": "2024-11-30T11:00:00Z",
                },
            ],
        }

        with patch.dict(os.environ, {"NEWSCLIENT_API_KEY": "test_key"}):
            with patch("veritas_news.worker.news_worker.NewsApiClient") as mock_newsapi:
                mock_client = MagicMock()
                mock_client.get_top_headlines.return_value = mock_response
                mock_newsapi.return_value = mock_client

                articles = await worker.fetch_newsapi_headlines()

        # Only the article with a valid URL should be included
        assert len(articles) == 1
        assert articles[0]["title"] == "Article with URL"


class TestURLConstructionBugs:
    """Test for common URL construction bugs"""

    def test_no_double_slash_when_joining_paths(self):
        """Test that joining URL parts doesn't create double slashes"""
        base_url = "http://localhost:8000/"
        endpoint = "/summarize"

        # Bug: Naive concatenation creates double slash
        bad_url = f"{base_url}{endpoint}"
        assert "//" in bad_url.replace("://", ""), "Test setup: should have double slash"

        # Fix: Strip slashes properly
        good_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        assert is_valid_url(good_url), f"Fixed URL should be valid: {good_url}"

    def test_article_url_not_corrupted_by_whitespace(self):
        """Test that URLs with whitespace are properly trimmed"""
        urls_with_whitespace = [
            "  https://example.com/article  ",
            "\thttps://example.com/article\t",
            "\nhttps://example.com/article\n",
        ]

        for url in urls_with_whitespace:
            cleaned = url.strip()
            assert is_valid_url(cleaned), f"Cleaned URL should be valid: {cleaned}"
            assert " " not in cleaned
            assert "\t" not in cleaned
            assert "\n" not in cleaned


class TestEndToEndURLFlow:
    """Test complete URL flow from fetch to storage to retrieval"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing with SQLAlchemy"""
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

    @pytest.fixture
    def worker(self):
        """Create NewsWorker instance"""
        return NewsWorker()

    @pytest.mark.asyncio
    async def test_fetch_store_retrieve_url_integrity(self, temp_db, worker):
        """Test complete flow: fetch articles, store, retrieve - URLs should match"""
        from veritas_news.db.init_db import get_connection
        from datetime import UTC, datetime

        # Mock RSS articles with test data
        test_articles = [
            {"title": "Test 1", "source": "Test", "url": "https://example.com/article1", "raw_text": "Content", "published_at": datetime.now(UTC)},
            {"title": "Test 2", "source": "Test", "url": "https://example.com/article2", "raw_text": "Content", "published_at": datetime.now(UTC)},
        ]
        original_urls = {a["url"] for a in test_articles}

        # Store articles - process_articles is now async
        stored_count = await worker.process_articles(test_articles, run_llm=False)
        assert stored_count > 0, "Should have stored at least one article"

        # Retrieve and verify URLs
        with get_connection() as session:
            stored_articles = session.query(Article).all()
            stored_urls = {a.url for a in stored_articles}

            # All original URLs should be in stored URLs
            for url in original_urls:
                assert url in stored_urls, f"URL not found in database: {url}"

            # All stored URLs should be valid
            for url in stored_urls:
                assert is_valid_url(url), f"Invalid URL retrieved from database: {url}"

    @pytest.mark.asyncio
    async def test_url_remains_accessible_format_after_processing(self, temp_db, worker):
        """Test that URLs remain in a format that could be accessed by a browser"""
        from veritas_news.db.init_db import get_connection

        # Create test article with a realistic URL
        test_url = f"https://www.example-news.com/2024/11/30/test-article-{uuid.uuid4()}"

        article = {
            "title": "Test Article",
            "source": "Example News",
            "url": test_url,
            "raw_text": "Test content",
            "published_at": datetime.now(UTC),
        }

        with get_connection() as session:
            worker.store_article(session, article)
            session.commit()

            stored = session.query(Article).filter_by(url=test_url).first()

            # URL should be valid and accessible format
            assert stored is not None
            assert is_valid_url(stored.url)

            # URL should have proper scheme for browser access
            parsed = urlparse(stored.url)
            assert parsed.scheme in ("http", "https")

            # URL should have valid domain
            assert has_valid_domain(stored.url)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


class TestRSSFetcherURLs:
    """Test URL accuracy when fetching from RSS feeds via RSSFetcher"""

    @pytest.fixture
    def rss_fetcher(self):
        """Create RSSFetcher instance with mock feeds"""
        from veritas_news.worker.fetchers import RSSFetcher
        return RSSFetcher(feeds=["https://example.com/feed.rss"], limit_per_feed=5)

    @pytest.mark.asyncio
    async def test_rss_fetcher_extracts_real_urls_from_feed(self):
        """Test that RSSFetcher extracts actual article URLs from RSS entries, not generated ones"""
        from veritas_news.worker.fetchers import RSSFetcher

        expected_url = "https://www.realnews.com/2024/11/30/actual-article-12345"

        mock_rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test News Feed</title>
                <item>
                    <title>Test Article Title</title>
                    <link>{expected_url}</link>
                    <description>Test article description</description>
                    <pubDate>Sat, 30 Nov 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            fetcher = RSSFetcher(feeds=["https://example.com/feed.rss"], limit_per_feed=5)
            articles = await fetcher.fetch_articles()

        assert len(articles) == 1
        # URL should be the actual link from RSS, not a generated URL
        assert articles[0].url == expected_url
        # URL should NOT contain the feed URL
        assert "example.com/feed.rss" not in articles[0].url

    @pytest.mark.asyncio
    async def test_rss_fetcher_urls_are_valid_format(self):
        """Test that RSSFetcher produces valid URLs"""
        from veritas_news.worker.fetchers import RSSFetcher

        mock_rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test News Feed</title>
                <item>
                    <title>Article 1</title>
                    <link>https://news.example.com/article/123</link>
                    <description>Description 1</description>
                    <pubDate>Sat, 30 Nov 2024 12:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Article 2</title>
                    <link>https://www.othernews.com/2024/story-456</link>
                    <description>Description 2</description>
                    <pubDate>Sat, 30 Nov 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            fetcher = RSSFetcher(feeds=["https://example.com/feed.rss"], limit_per_feed=5)
            articles = await fetcher.fetch_articles()

        assert len(articles) == 2
        for article in articles:
            assert is_valid_url(article.url), f"Invalid URL: {article.url}"
            # Ensure URL doesn't contain feed URL path
            assert "/feed.rss" not in article.url

    @pytest.mark.asyncio
    async def test_rss_fetcher_skips_entries_without_urls(self):
        """Test that entries without link elements are skipped"""
        from veritas_news.worker.fetchers import RSSFetcher

        mock_rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test News Feed</title>
                <item>
                    <title>Article with URL</title>
                    <link>https://news.example.com/article/123</link>
                    <description>Has URL</description>
                </item>
                <item>
                    <title>Article without URL</title>
                    <description>No URL here</description>
                </item>
            </channel>
        </rss>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            fetcher = RSSFetcher(feeds=["https://example.com/feed.rss"], limit_per_feed=5)
            articles = await fetcher.fetch_articles()

        # Only the article with a URL should be returned
        assert len(articles) == 1
        assert articles[0].url == "https://news.example.com/article/123"

    @pytest.mark.asyncio
    async def test_rss_fetcher_handles_feed_errors_gracefully(self):
        """Test that RSSFetcher handles HTTP errors without crashing"""
        import httpx

        from veritas_news.worker.fetchers import RSSFetcher

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=MagicMock()
            ))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            fetcher = RSSFetcher(feeds=["https://example.com/broken-feed.rss"], limit_per_feed=5)
            articles = await fetcher.fetch_articles()

        # Should return empty list, not crash
        assert articles == []


class TestRealURLAccessibility:
    """
    Integration tests to verify URLs are actually accessible.
    These tests make real network requests and should be skipped in CI.
    """

    @pytest.fixture
    def worker(self):
        """Create NewsWorker instance"""
        return NewsWorker(hours_back=24, limit=3)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test - requires network access")
    async def test_cnn_rss_urls_are_reachable(self, worker):
        """Test that URLs from CNN RSS feed are actually reachable"""
        import httpx

        articles = await worker.fetch_cnn_articles()

        if not articles:
            pytest.skip("No articles returned from CNN RSS")

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; test-bot)"},
        ) as client:
            for article in articles[:3]:  # Test first 3 articles
                url = article["url"]

                try:
                    response = await client.head(url)
                    # Accept 2xx and 3xx status codes
                    assert response.status_code < 400, \
                        f"URL returned error status {response.status_code}: {url}"
                except httpx.RequestError as e:
                    pytest.fail(f"Failed to reach URL {url}: {e}")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test - requires API key")
    async def test_newsapi_urls_are_reachable(self, worker):
        """Test that URLs from NewsAPI are actually reachable"""
        import httpx

        articles = await worker.fetch_newsapi_headlines()

        if not articles:
            pytest.skip("No articles returned from NewsAPI")

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; test-bot)"},
        ) as client:
            for article in articles[:3]:  # Test first 3 articles
                url = article["url"]

                try:
                    response = await client.head(url)
                    # Accept 2xx and 3xx status codes
                    assert response.status_code < 400, \
                        f"URL returned error status {response.status_code}: {url}"
                except httpx.RequestError as e:
                    pytest.fail(f"Failed to reach URL {url}: {e}")


class TestURLIssuesDiagnosis:
    """
    Tests to diagnose common URL issues that cause links to not work.
    """

    def test_url_join_helper_prevents_double_slashes(self):
        """Test a helper function that safely joins URL parts"""
        def safe_url_join(base: str, path: str) -> str:
            """Safely join URL base and path without double slashes"""
            return f"{base.rstrip('/')}/{path.lstrip('/')}"

        test_cases = [
            ("http://example.com", "api/articles", "http://example.com/api/articles"),
            ("http://example.com/", "api/articles", "http://example.com/api/articles"),
            ("http://example.com", "/api/articles", "http://example.com/api/articles"),
            ("http://example.com/", "/api/articles", "http://example.com/api/articles"),
        ]

        for base, path, expected in test_cases:
            result = safe_url_join(base, path)
            assert result == expected, f"safe_url_join({base}, {path}) = {result}, expected {expected}"
            assert is_valid_url(result), f"Result is not a valid URL: {result}"
