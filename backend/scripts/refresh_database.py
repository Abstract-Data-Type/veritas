#!/usr/bin/env python3
"""
Database Refresh Script for Veritas News

This script provides utilities to:
1. Initialize a fresh database
2. Fetch new articles from RSS feeds
3. Analyze bias for all articles
4. Remove old articles (optional)
5. Verify database integrity

Usage:
    # Initialize fresh database with new articles
    python scripts/refresh_database.py --init

    # Add new articles to existing database
    python scripts/refresh_database.py --fetch

    # Analyze bias for articles missing ratings
    python scripts/refresh_database.py --analyze

    # Remove articles older than N days
    python scripts/refresh_database.py --cleanup --days 7

    # Full refresh: init + fetch + analyze
    python scripts/refresh_database.py --full

    # Show database status
    python scripts/refresh_database.py --status
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from veritas_news.ai import rate_bias, rate_secm
from veritas_news.db.sqlalchemy import Base, SessionLocal, engine
from veritas_news.models.bias_rating import normalize_score_to_range
from veritas_news.models.sqlalchemy_models import Article, BiasRating, Summary
from veritas_news.worker.news_worker import NewsWorker


class DatabaseRefresher:
    """Utility class for database operations"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.setup_logging()

    def setup_logging(self):
        """Configure logging"""
        logger.remove()
        level = "DEBUG" if self.verbose else "INFO"
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>"
        )

    def get_session(self) -> Session:
        """Get a database session"""
        return SessionLocal()

    def init_database(self, drop_existing: bool = False) -> bool:
        """
        Initialize the database, optionally dropping existing tables.

        Args:
            drop_existing: If True, drop all tables before creating

        Returns:
            bool: True if successful
        """
        try:
            if drop_existing:
                logger.warning("Dropping all existing tables...")
                Base.metadata.drop_all(bind=engine)
                logger.info("All tables dropped")

            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    async def fetch_articles(self, limit: int = 10, sources: list = None) -> int:
        """
        Fetch new articles from RSS feeds.

        Args:
            limit: Maximum articles per source
            sources: List of RSS feed URLs (uses defaults if None)

        Returns:
            int: Number of articles fetched
        """
        logger.info(f"Fetching articles (limit: {limit} per source)...")

        worker = NewsWorker(hours_back=24, limit=limit)

        # Fetch from RSS feeds
        articles = await worker.fetch_rss_articles()

        if not articles:
            logger.warning("No articles fetched from RSS feeds")
            return 0

        logger.info(f"Fetched {len(articles)} articles from RSS feeds")

        # Store articles (this also triggers bias analysis now)
        stored_count = await worker.process_articles(articles)

        logger.info(f"Stored {stored_count} new articles")
        return stored_count

    async def analyze_missing_bias(self, batch_size: int = 10) -> int:
        """
        Analyze bias for articles that don't have ratings.

        Args:
            batch_size: Number of articles to process at once

        Returns:
            int: Number of articles analyzed
        """
        logger.info("Finding articles without bias ratings...")

        db = self.get_session()
        try:
            # Find articles without bias ratings
            articles_without_ratings = db.query(Article).outerjoin(
                BiasRating, Article.article_id == BiasRating.article_id
            ).filter(BiasRating.rating_id is None).all()

            if not articles_without_ratings:
                logger.info("All articles have bias ratings")
                return 0

            logger.info(f"Found {len(articles_without_ratings)} articles without ratings")

            analyzed_count = 0
            for article in articles_without_ratings:
                if not article.raw_text or len(article.raw_text.strip()) < 50:
                    logger.debug(f"Skipping article {article.article_id}: text too short")
                    continue

                try:
                    logger.info(f"Analyzing: {article.title[:50]}...")
                    
                    # Run legacy 4-dimension bias analysis
                    bias_result = await rate_bias(article.raw_text)

                    scores = bias_result.get("scores", {})
                    partisan_bias = scores.get("partisan_bias")
                    affective_bias = scores.get("affective_bias")
                    framing_bias = scores.get("framing_bias")
                    sourcing_bias = scores.get("sourcing_bias")

                    valid_scores = [s for s in [partisan_bias, affective_bias, framing_bias, sourcing_bias] if s is not None]
                    if valid_scores:
                        avg_score = sum(valid_scores) / len(valid_scores)
                        overall_bias_score = normalize_score_to_range(avg_score)
                    else:
                        overall_bias_score = None

                    # Run SECM analysis (22 parallel LLM calls)
                    try:
                        secm_result = await rate_secm(article.raw_text)
                        secm_ideological = secm_result.get("ideological_score")
                        secm_epistemic = secm_result.get("epistemic_score")
                        secm_variables = secm_result.get("variables", {})
                        secm_reasoning = secm_result.get("reasoning", {})
                    except Exception as e:
                        logger.warning(f"SECM analysis failed: {e}")
                        secm_ideological = None
                        secm_epistemic = None
                        secm_variables = {}
                        secm_reasoning = {}

                    import json
                    new_rating = BiasRating(
                        article_id=article.article_id,
                        bias_score=overall_bias_score,
                        partisan_bias=partisan_bias,
                        affective_bias=affective_bias,
                        framing_bias=framing_bias,
                        sourcing_bias=sourcing_bias,
                        reasoning=None,
                        evaluated_at=datetime.now(UTC),
                        # SECM fields
                        secm_ideological_score=secm_ideological,
                        secm_epistemic_score=secm_epistemic,
                        secm_ideol_l1_systemic_naming=secm_variables.get("secm_ideol_l1_systemic_naming"),
                        secm_ideol_l2_power_gap_lexicon=secm_variables.get("secm_ideol_l2_power_gap_lexicon"),
                        secm_ideol_l3_elite_culpability=secm_variables.get("secm_ideol_l3_elite_culpability"),
                        secm_ideol_l4_resource_redistribution=secm_variables.get("secm_ideol_l4_resource_redistribution"),
                        secm_ideol_l5_change_as_justice=secm_variables.get("secm_ideol_l5_change_as_justice"),
                        secm_ideol_l6_care_harm=secm_variables.get("secm_ideol_l6_care_harm"),
                        secm_ideol_r1_agentic_culpability=secm_variables.get("secm_ideol_r1_agentic_culpability"),
                        secm_ideol_r2_order_lexicon=secm_variables.get("secm_ideol_r2_order_lexicon"),
                        secm_ideol_r3_institutional_defense=secm_variables.get("secm_ideol_r3_institutional_defense"),
                        secm_ideol_r4_meritocratic_defense=secm_variables.get("secm_ideol_r4_meritocratic_defense"),
                        secm_ideol_r5_change_as_threat=secm_variables.get("secm_ideol_r5_change_as_threat"),
                        secm_ideol_r6_sanctity_degradation=secm_variables.get("secm_ideol_r6_sanctity_degradation"),
                        secm_epist_h1_primary_documentation=secm_variables.get("secm_epist_h1_primary_documentation"),
                        secm_epist_h2_adversarial_sourcing=secm_variables.get("secm_epist_h2_adversarial_sourcing"),
                        secm_epist_h3_specific_attribution=secm_variables.get("secm_epist_h3_specific_attribution"),
                        secm_epist_h4_data_contextualization=secm_variables.get("secm_epist_h4_data_contextualization"),
                        secm_epist_h5_methodological_transparency=secm_variables.get("secm_epist_h5_methodological_transparency"),
                        secm_epist_e1_emotive_adjectives=secm_variables.get("secm_epist_e1_emotive_adjectives"),
                        secm_epist_e2_labeling_othering=secm_variables.get("secm_epist_e2_labeling_othering"),
                        secm_epist_e3_causal_certainty=secm_variables.get("secm_epist_e3_causal_certainty"),
                        secm_epist_e4_imperative_direct_address=secm_variables.get("secm_epist_e4_imperative_direct_address"),
                        secm_epist_e5_motivated_reasoning=secm_variables.get("secm_epist_e5_motivated_reasoning"),
                        secm_reasoning_json=json.dumps(secm_reasoning) if secm_reasoning else None,
                    )

                    db.add(new_rating)
                    db.commit()

                    analyzed_count += 1
                    secm_str = f", SECM ideo={secm_ideological:+.2f}" if secm_ideological else ""
                    logger.info(f"  → Bias score: {overall_bias_score:.2f}{secm_str}" if overall_bias_score else "  → No score")

                except Exception as e:
                    logger.error(f"Error analyzing article {article.article_id}: {e}")
                    db.rollback()

            return analyzed_count

        finally:
            db.close()

    def clear_all_ratings(self) -> int:
        """
        Delete all bias ratings to force re-analysis.

        Returns:
            int: Number of ratings deleted
        """
        logger.info("Clearing all existing bias ratings...")

        db = self.get_session()
        try:
            deleted_count = db.query(BiasRating).delete()
            db.commit()
            logger.info(f"Deleted {deleted_count} bias ratings")
            return deleted_count
        except Exception as e:
            logger.error(f"Error clearing ratings: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def cleanup_old_articles(self, days: int = 7) -> int:
        """
        Remove articles older than specified days.

        Args:
            days: Remove articles older than this many days

        Returns:
            int: Number of articles removed
        """
        logger.info(f"Removing articles older than {days} days...")

        db = self.get_session()
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            # First delete associated bias ratings
            old_article_ids = db.query(Article.article_id).filter(
                Article.created_at < cutoff_date
            ).all()
            old_ids = [a[0] for a in old_article_ids]

            if not old_ids:
                logger.info("No old articles to remove")
                return 0

            # Delete bias ratings for old articles
            deleted_ratings = db.query(BiasRating).filter(
                BiasRating.article_id.in_(old_ids)
            ).delete(synchronize_session=False)

            # Delete summaries for old articles
            deleted_summaries = db.query(Summary).filter(
                Summary.article_id.in_(old_ids)
            ).delete(synchronize_session=False)

            # Delete old articles
            deleted_articles = db.query(Article).filter(
                Article.article_id.in_(old_ids)
            ).delete(synchronize_session=False)

            db.commit()

            logger.info(f"Removed {deleted_articles} articles, {deleted_ratings} bias ratings, {deleted_summaries} summaries")
            return deleted_articles

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def show_status(self):
        """Display current database status"""
        db = self.get_session()
        try:
            total_articles = db.query(Article).count()
            total_ratings = db.query(BiasRating).count()
            total_summaries = db.query(Summary).count()

            articles_with_ratings = db.query(Article).join(
                BiasRating, Article.article_id == BiasRating.article_id
            ).count()

            articles_without_ratings = total_articles - articles_with_ratings

            # Get article distribution by source
            sources = db.query(
                Article.source,
                func.count(Article.article_id).label("count")
            ).group_by(Article.source).all()

            # Get bias distribution
            left_count = db.query(BiasRating).filter(BiasRating.bias_score < -0.25).count()
            center_count = db.query(BiasRating).filter(
                BiasRating.bias_score >= -0.25,
                BiasRating.bias_score <= 0.25
            ).count()
            right_count = db.query(BiasRating).filter(BiasRating.bias_score > 0.25).count()

            # Get recent articles
            recent = db.query(Article).order_by(Article.created_at.desc()).limit(5).all()

            print("\n" + "=" * 60)
            print("VERITAS NEWS DATABASE STATUS")
            print("=" * 60)
            print("\n📊 TOTALS:")
            print(f"   Articles:      {total_articles}")
            print(f"   Bias Ratings:  {total_ratings}")
            print(f"   Summaries:     {total_summaries}")
            print("\n📈 COVERAGE:")
            print(f"   With ratings:    {articles_with_ratings}")
            print(f"   Without ratings: {articles_without_ratings}")
            print("\n🎯 BIAS DISTRIBUTION:")
            print(f"   Left:   {left_count} articles")
            print(f"   Center: {center_count} articles")
            print(f"   Right:  {right_count} articles")
            print("\n📰 SOURCES:")
            for source, count in sources:
                print(f"   {source or 'Unknown'}: {count}")
            print("\n🕐 RECENT ARTICLES:")
            for article in recent:
                rating = db.query(BiasRating).filter(
                    BiasRating.article_id == article.article_id
                ).first()
                bias_str = f"{rating.bias_score:.2f}" if rating and rating.bias_score is not None else "N/A"
                print(f"   [{bias_str:>6}] {article.title[:50]}...")
            print("\n" + "=" * 60)

        finally:
            db.close()

    def verify_integrity(self) -> bool:
        """
        Verify database integrity.

        Returns:
            bool: True if all checks pass
        """
        logger.info("Verifying database integrity...")

        db = self.get_session()
        try:
            issues = []

            # Check for orphaned bias ratings
            orphaned_ratings = db.query(BiasRating).outerjoin(
                Article, BiasRating.article_id == Article.article_id
            ).filter(Article.article_id is None).count()

            if orphaned_ratings > 0:
                issues.append(f"Found {orphaned_ratings} orphaned bias ratings")

            # Check for articles with null titles
            null_titles = db.query(Article).filter(
                Article.title is None
            ).count()

            if null_titles > 0:
                issues.append(f"Found {null_titles} articles with null titles")

            # Check for duplicate URLs
            duplicates = db.query(
                Article.url, func.count(Article.url).label("count")
            ).group_by(Article.url).having(func.count(Article.url) > 1).all()

            if duplicates:
                issues.append(f"Found {len(duplicates)} duplicate URLs")

            if issues:
                logger.warning("Database integrity issues found:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                return False
            else:
                logger.info("Database integrity check passed ✓")
                return True

        finally:
            db.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Veritas News Database Refresh Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/refresh_database.py --init              # Fresh database
  python scripts/refresh_database.py --fetch --limit 20  # Fetch 20 articles
  python scripts/refresh_database.py --analyze           # Analyze missing bias
  python scripts/refresh_database.py --cleanup --days 3  # Remove old articles
  python scripts/refresh_database.py --full              # Complete refresh
  python scripts/refresh_database.py --status            # Show status
        """
    )

    parser.add_argument("--init", action="store_true",
                        help="Initialize fresh database (drops existing data)")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch new articles from RSS feeds")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze bias for articles without ratings")
    parser.add_argument("--reanalyze", action="store_true",
                        help="Clear all ratings and re-analyze ALL articles")
    parser.add_argument("--cleanup", action="store_true",
                        help="Remove old articles")
    parser.add_argument("--full", action="store_true",
                        help="Full refresh: init + fetch + analyze")
    parser.add_argument("--status", action="store_true",
                        help="Show database status")
    parser.add_argument("--verify", action="store_true",
                        help="Verify database integrity")

    parser.add_argument("--limit", type=int, default=10,
                        help="Max articles to fetch per source (default: 10)")
    parser.add_argument("--days", type=int, default=7,
                        help="Days to keep articles (default: 7)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--keep-existing", action="store_true",
                        help="Don't drop existing tables during --init")

    args = parser.parse_args()

    # Check if no action specified
    if not any([args.init, args.fetch, args.analyze, args.reanalyze, args.cleanup,
                args.full, args.status, args.verify]):
        parser.print_help()
        return

    # Check for required environment variables
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY not set - bias analysis will fail")

    refresher = DatabaseRefresher(verbose=args.verbose)

    # Handle --full as combination of init + fetch + analyze
    if args.full:
        args.init = True
        args.fetch = True
        args.analyze = True

    # Execute requested operations
    if args.init:
        success = refresher.init_database(drop_existing=not args.keep_existing)
        if not success:
            logger.error("Database initialization failed")
            return

    if args.fetch:
        await refresher.fetch_articles(limit=args.limit)

    if args.reanalyze:
        refresher.clear_all_ratings()
        await refresher.analyze_missing_bias()
    elif args.analyze:
        await refresher.analyze_missing_bias()

    if args.cleanup:
        refresher.cleanup_old_articles(days=args.days)

    if args.verify:
        refresher.verify_integrity()

    if args.status:
        refresher.show_status()


if __name__ == "__main__":
    asyncio.run(main())
