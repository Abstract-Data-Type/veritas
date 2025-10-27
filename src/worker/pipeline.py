import sqlite3
from typing import List, Optional, Set
from datetime import datetime
from loguru import logger
import httpx
import os

from .fetchers import ArticleData
from ..db.init_db import get_connection


class ArticlePipeline:
    """Pipeline for processing and storing articles"""
    
    def __init__(self):
        self._processed_urls: Set[str] = set()
        self.summarization_service_url = os.environ.get(
            "SUMMARIZATION_SERVICE_URL",
            "http://localhost:8000"
        )
    
    async def _get_article_summary(self, article_text: str) -> Optional[str]:
        """
        Get a summary of the article text from the summarization service.
        
        Args:
            article_text: The full text of the article
            
        Returns:
            Summary string or None if summarization fails
        """
        if not article_text or len(article_text.strip()) < 50:
            logger.debug("Article text too short for summarization, skipping")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.summarization_service_url}/summarize",
                    json={"article_text": article_text}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    summary = data.get("summary", "")
                    logger.debug(f"Generated summary: {summary[:100]}...")
                    return summary
                else:
                    logger.warning(f"Summarization service returned {response.status_code}")
                    return None
        
        except httpx.TimeoutException:
            logger.warning("Summarization service timeout, continuing without summary")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Cannot reach summarization service: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return None
    
    def _normalize_article(self, article: ArticleData) -> ArticleData:
        """Basic article normalization"""
        # Strip whitespace and normalize title
        article.title = article.title.strip()
        article.raw_text = article.raw_text.strip()
        article.url = article.url.strip()
        
        # Ensure we have required fields
        if not article.title:
            article.title = "Untitled Article"
        if not article.raw_text:
            article.raw_text = "No content available"
        
        return article
    
    def _is_duplicate(self, conn: sqlite3.Connection, article: ArticleData) -> bool:
        """Check if article already exists in database"""
        cursor = conn.cursor()
        
        # Check by URL first (exact match)
        cursor.execute("SELECT 1 FROM articles WHERE url = ?", (article.url,))
        if cursor.fetchone():
            return True
        
        # Check by title similarity (basic exact match for now)
        cursor.execute("SELECT 1 FROM articles WHERE title = ?", (article.title,))
        if cursor.fetchone():
            return True
        
        # Check in-memory processed URLs
        if article.url in self._processed_urls:
            return True
        
        return False
    
    def _store_article(self, conn: sqlite3.Connection, article: ArticleData) -> Optional[int]:
        """Store article in database and return article_id"""
        try:
            cursor = conn.cursor()
            
            # Convert datetime to string for SQLite
            published_at_str = article.published_at.isoformat() if article.published_at else None
            
            query = """
            INSERT INTO articles (title, source, url, published_at, raw_text, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            cursor.execute(query, (
                article.title,
                article.source,
                article.url,
                published_at_str,
                article.raw_text
            ))
            
            conn.commit()
            article_id = cursor.lastrowid
            
            # Add to processed URLs set
            self._processed_urls.add(article.url)
            
            logger.info(f"Stored article: {article.title} (ID: {article_id})")
            return article_id
            
        except sqlite3.Error as e:
            logger.error(f"Database error storing article '{article.title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error storing article '{article.title}': {e}")
            return None
    
    def process_articles(self, articles: List[ArticleData]) -> List[int]:
        """Process and store a batch of articles"""
        logger.info(f"Processing {len(articles)} articles")
        
        if not articles:
            return []
        
        stored_ids = []
        conn = None
        
        try:
            conn = get_connection()
            
            new_articles = 0
            duplicates = 0
            errors = 0
            
            for article in articles:
                try:
                    # Normalize the article
                    normalized_article = self._normalize_article(article)
                    
                    # Check for duplicates
                    if self._is_duplicate(conn, normalized_article):
                        logger.debug(f"Duplicate article skipped: {normalized_article.title}")
                        duplicates += 1
                        continue
                    
                    # Store the article
                    article_id = self._store_article(conn, normalized_article)
                    if article_id:
                        stored_ids.append(article_id)
                        new_articles += 1
                    else:
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Error processing individual article: {e}")
                    errors += 1
            
            logger.info(f"Processing complete: {new_articles} new, {duplicates} duplicates, {errors} errors")
            
        except Exception as e:
            logger.error(f"Error in process_articles: {e}")
        finally:
            if conn:
                conn.close()
        
        return stored_ids
    
    def get_recent_articles(self, limit: int = 10) -> List[dict]:
        """Get recently stored articles for verification"""
        conn = None
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT article_id, title, source, url, published_at, created_at
            FROM articles
            ORDER BY created_at DESC
            LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_article_count(self) -> int:
        """Get total number of articles in database"""
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting article count: {e}")
            return 0
        finally:
            if conn:
                conn.close()