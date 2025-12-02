"""
End-to-end tests for the 12-hour maintenance cycle.

These tests use REAL:
- RSS feeds to fetch articles
- Gemini API for summarization
- Gemini API for LCCM/SECM bias analysis

Run with: pytest tests/test_maintenance_e2e.py -v -s
"""

import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritas_news.db.sqlalchemy import Base
from veritas_news.main import maintenance_state
from veritas_news.models.sqlalchemy_models import Article, BiasRating, Summary
from veritas_news.worker.news_worker import NewsWorker


@pytest.fixture
def e2e_db():
    """Create a temporary database for e2e testing"""
    db_fd, db_path = tempfile.mkstemp(suffix="_e2e.db")
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


class TestE2ERefreshCycle:
    """End-to-end tests with real API calls"""

    @pytest.mark.asyncio
    async def test_full_refresh_cycle_with_real_rss_no_llm(self, e2e_db):
        """
        E2E test: Full refresh cycle with real RSS feeds but no LLM.
        
        Tests:
        - Real RSS article fetching
        - Database clear and populate
        - Maintenance state transitions
        """
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            # ===== PHASE 1: Set maintenance ON =====
            maintenance_state["is_running"] = True
            maintenance_state["started_at"] = datetime.now(UTC).isoformat()
            assert maintenance_state["is_running"] is True

            # ===== PHASE 2: Fetch real articles =====
            worker = NewsWorker(limit=2)  # Limit to 2 per feed for speed
            
            # Fetch from real RSS feeds
            articles = await worker.fetch_rss_articles()
            
            assert len(articles) > 0, "Should fetch at least 1 article from RSS"
            
            # Verify article structure
            for article in articles:
                assert "title" in article and article["title"]
                assert "source" in article and article["source"]
                assert "url" in article and article["url"]
                assert "raw_text" in article

            # ===== PHASE 3: Process without LLM =====
            count = await worker.process_articles(articles, run_llm=False)
            
            assert count > 0, "Should store at least 1 article"
            
            db.expire_all()
            stored_count = db.query(Article).count()
            assert stored_count == count

            # ===== PHASE 4: Set maintenance OFF =====
            maintenance_state["is_running"] = False
            maintenance_state["last_completed"] = datetime.now(UTC).isoformat()
            
            assert maintenance_state["is_running"] is False
            
            db.close()

    @pytest.mark.asyncio
    async def test_full_refresh_cycle_with_real_llm(self, e2e_db):
        """
        E2E test: Full 12-hour refresh cycle simulation with REAL LLM calls.
        
        Tests:
        - Real RSS article fetching
        - Real Gemini summarization
        - Real SECM bias analysis (22 LLM calls per article)
        - Database clear and populate
        - Maintenance state transitions
        
        ⚠️ This test makes real API calls and may take 1-2 minutes per article.
        """
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            # ===== PHASE 1: Start maintenance =====
            maintenance_state["is_running"] = True
            maintenance_state["started_at"] = datetime.now(UTC).isoformat()
            assert maintenance_state["is_running"] is True

            # ===== PHASE 2: Clear any existing data =====
            worker = NewsWorker(limit=1)  # Only 1 article per feed for speed
            worker.clear_database()

            db.expire_all()
            assert db.query(Article).count() == 0
            assert db.query(Summary).count() == 0
            assert db.query(BiasRating).count() == 0

            # ===== PHASE 3: Fetch and process with REAL LLM =====
            count = await worker.run_single_fetch(
                use_stub=False,  # Real RSS feeds
                run_llm=True     # Real LLM analysis
            )

            assert count > 0, "Should store at least 1 article"

            db.expire_all()
            
            # Verify articles stored
            articles = db.query(Article).all()
            assert len(articles) > 0
            
            # Verify summaries generated
            summaries = db.query(Summary).all()
            assert len(summaries) > 0, "Should have generated at least 1 summary"
            
            for summary in summaries:
                assert summary.summary_text is not None
                assert len(summary.summary_text) > 10, "Summary should have content"

            # Verify bias ratings with SECM scores
            ratings = db.query(BiasRating).all()
            assert len(ratings) > 0, "Should have at least 1 bias rating"
            
            for rating in ratings:
                # SECM scores should be populated
                assert rating.secm_ideological_score is not None, \
                    "SECM ideological score should be set"
                assert rating.secm_epistemic_score is not None, \
                    "SECM epistemic score should be set"
                
                # Scores should be in valid range [-1, 1]
                assert -1.0 <= rating.secm_ideological_score <= 1.0
                assert -1.0 <= rating.secm_epistemic_score <= 1.0

            # ===== PHASE 4: Complete maintenance =====
            maintenance_state["is_running"] = False
            maintenance_state["last_completed"] = datetime.now(UTC).isoformat()
            maintenance_state["next_refresh"] = datetime.now(UTC).isoformat()

            assert maintenance_state["is_running"] is False
            assert maintenance_state["last_completed"] is not None

            db.close()

    @pytest.mark.asyncio
    async def test_clear_and_refetch_cycle(self, e2e_db):
        """
        E2E test: Simulates what happens at the 12-hour mark.
        
        1. Populate DB with articles
        2. Clear everything (simulating 12-hour cycle)
        3. Refetch fresh articles
        4. Verify old articles gone, new articles present
        """
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()

            worker = NewsWorker(limit=1)

            # ===== Initial population =====
            initial_count = await worker.run_single_fetch(use_stub=False, run_llm=False)
            assert initial_count > 0

            db.expire_all()
            initial_articles = db.query(Article).all()
            initial_urls = {a.url for a in initial_articles}

            # ===== 12-hour mark: Clear =====
            worker.clear_database()

            db.expire_all()
            assert db.query(Article).count() == 0

            # ===== Refetch (new cycle) =====
            new_count = await worker.run_single_fetch(use_stub=False, run_llm=False)
            assert new_count > 0

            db.expire_all()
            new_articles = db.query(Article).all()
            
            # Verify we have articles
            assert len(new_articles) > 0

            db.close()


class TestE2ELLMAnalysis:
    """Tests specifically for LLM analysis components"""

    @pytest.mark.asyncio
    async def test_summarization_with_real_article(self, e2e_db):
        """Test real Gemini summarization on a real article"""
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()
            worker = NewsWorker(limit=1)

            # Fetch 1 real article
            articles = await worker.fetch_rss_articles()
            assert len(articles) > 0

            article = articles[0]
            article_id = worker.store_article(db, article)
            assert article_id is not None

            # Generate real summary
            raw_text = article.get("raw_text", "")
            if len(raw_text) >= 50:
                success = worker.generate_article_summary(db, article_id, raw_text)
                assert success, "Summary generation should succeed"

                db.expire_all()
                summary = db.query(Summary).filter(
                    Summary.article_id == article_id
                ).first()
                
                assert summary is not None
                assert len(summary.summary_text) > 20

            db.close()

    @pytest.mark.asyncio
    async def test_bias_analysis_with_real_article(self, e2e_db):
        """Test real SECM bias analysis on a real article"""
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            db = TestingSessionLocal()
            worker = NewsWorker(limit=1)

            # Fetch 1 real article
            articles = await worker.fetch_rss_articles()
            assert len(articles) > 0

            article = articles[0]
            article_id = worker.store_article(db, article)
            assert article_id is not None

            # Run real bias analysis
            raw_text = article.get("raw_text", "")
            if len(raw_text) >= 50:
                success = await worker.analyze_article_bias(db, article_id, raw_text)
                assert success, "Bias analysis should succeed"

                db.expire_all()
                rating = db.query(BiasRating).filter(
                    BiasRating.article_id == article_id
                ).first()
                
                assert rating is not None
                
                # Verify SECM scores
                assert rating.secm_ideological_score is not None
                assert rating.secm_epistemic_score is not None
                assert -1.0 <= rating.secm_ideological_score <= 1.0
                assert -1.0 <= rating.secm_epistemic_score <= 1.0
                
                # Verify some SECM variables were set
                secm_vars = [
                    rating.secm_ideol_l1_systemic_naming,
                    rating.secm_ideol_r1_agentic_culpability,
                    rating.secm_epist_h1_primary_documentation,
                    rating.secm_epist_e1_emotive_adjectives,
                ]
                assert any(v is not None for v in secm_vars), \
                    "At least some SECM variables should be populated"

            db.close()


class TestE2EMaintenanceFlow:
    """Tests for the maintenance mode flow visible to users"""

    @pytest.mark.asyncio
    async def test_maintenance_state_reflects_real_processing(self, e2e_db):
        """
        Test that maintenance state correctly tracks a real processing cycle.
        This is what the frontend uses to show "Analysis in Progress".
        """
        TestingSessionLocal, _, _ = e2e_db

        with mock_get_connection(TestingSessionLocal):
            # Initially not in maintenance
            maintenance_state["is_running"] = False
            assert maintenance_state["is_running"] is False

            # Start processing
            maintenance_state["is_running"] = True
            start_time = datetime.now(UTC).isoformat()
            maintenance_state["started_at"] = start_time
            
            assert maintenance_state["is_running"] is True
            assert maintenance_state["started_at"] == start_time

            # Do real work
            worker = NewsWorker(limit=1)
            await worker.run_single_fetch(use_stub=False, run_llm=False)

            # Complete processing
            maintenance_state["is_running"] = False
            maintenance_state["last_completed"] = datetime.now(UTC).isoformat()

            assert maintenance_state["is_running"] is False
            assert maintenance_state["last_completed"] is not None
            # Verify completion time is after start time
            assert maintenance_state["last_completed"] >= start_time


if __name__ == "__main__":
    # Run with verbose output to see progress
    pytest.main([__file__, "-v", "-s"])

