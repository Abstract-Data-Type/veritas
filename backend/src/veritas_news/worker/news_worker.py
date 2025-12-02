#!/usr/bin/env python3
"""
Simplified News Worker

Fetches articles from stubbed sources and stores them in the database.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import feedparser
import httpx
from loguru import logger
from newsapi import NewsApiClient
from sqlalchemy.orm import Session

from ..ai import rate_bias, rate_secm, summarize_with_gemini
from ..db.init_db import get_connection, init_db
from ..models.bias_rating import normalize_score_to_range
from ..models.sqlalchemy_models import Article, BiasRating, Summary

# Configuration
POLL_INTERVAL = 30 * 60  # 30 minutes in seconds
DEFAULT_HOURS_BACK = 1  # Default to last 1 hour
DEFAULT_ARTICLE_LIMIT = 5  # Default limit of 5 articles per feed


class NewsWorker:
    """Simple news worker that fetches and stores articles"""

    def __init__(
        self, hours_back: int = DEFAULT_HOURS_BACK, limit: int = DEFAULT_ARTICLE_LIMIT
    ):
        self.processed_urls: set[str] = set()
        self.running = False
        self.hours_back = hours_back
        self.limit = limit

    async def fetch_stubbed_articles(self) -> list[dict]:
        """Fetch articles from all stubbed sources - DEPRECATED, use fetch_rss_articles instead"""
        logger.warning("Using deprecated stubbed articles - these URLs are not real!")
        logger.info("Fetching articles from stubbed sources")

        # Simulate fetch delay
        await asyncio.sleep(0.5)

        # Return stubbed articles - NOTE: These URLs are fake and for testing only
        articles = [
            {
                "title": "Breaking: Tech Giant Announces New AI Initiative",
                "source": "TechNews (Stub)",
                "url": f"https://example.com/stub/ai-initiative-{datetime.now().timestamp()}",
                "raw_text": "Tech giant revealed plans for new AI initiative...",
                "published_at": datetime.now(UTC),
            },
            {
                "title": "Global Climate Summit Reaches Historic Agreement",
                "source": "WorldNews (Stub)",
                "url": f"https://example.com/stub/climate-summit-{datetime.now().timestamp()}",
                "raw_text": "World leaders reached historic agreement on carbon reduction...",
                "published_at": datetime.now(UTC),
            },
        ]

        logger.info(f"Fetched {len(articles)} stubbed articles")
        return articles

    async def fetch_rss_articles(self) -> list[dict]:
        """Fetch articles from configured RSS feeds"""
        from .config import WorkerConfig
        from .fetchers import RSSFetcher

        logger.info(f"Fetching articles from RSS feeds, limit {self.limit}")

        try:
            fetcher = RSSFetcher(WorkerConfig.RSS_FEEDS, limit_per_feed=self.limit)
            article_data_list = await fetcher.fetch_articles()

            # Convert ArticleData objects to dict format
            articles = []
            for article_data in article_data_list:
                articles.append({
                    "title": article_data.title,
                    "source": article_data.source,
                    "url": article_data.url,
                    "raw_text": article_data.raw_text,
                    "published_at": article_data.published_at,
                })

            logger.info(f"Fetched {len(articles)} RSS articles")
            return articles

        except Exception as e:
            logger.error(f"Error fetching RSS feeds: {e}")
            return []

    async def fetch_cnn_articles(self) -> list[dict]:
        """Fetch recent articles from CNN RSS feed"""
        logger.info(
            f"Fetching CNN articles from last {self.hours_back} hour(s), limit {self.limit}"
        )

        try:
            # CNN RSS feed URL
            rss_url = "http://rss.cnn.com/rss/cnn_topstories.rss"

            # Rate limiting - be respectful
            await asyncio.sleep(1.0)

            # Fetch RSS feed with custom headers to avoid blocking
            logger.debug(f"Fetching RSS from: {rss_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml",
            }

            async with httpx.AsyncClient(
                timeout=30.0,
                verify=False,  # Skip SSL verification for testing
                follow_redirects=True,
            ) as client:
                response = await client.get(rss_url, headers=headers)
                logger.debug(f"HTTP response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                response.raise_for_status()

            # Parse RSS feed
            logger.debug(f"Response content length: {len(response.text)}")
            logger.debug(f"Response content preview: {response.text[:200]}...")
            feed = feedparser.parse(response.text)
            logger.debug(f"Feedparser found {len(feed.entries)} entries")

            if not feed.entries:
                logger.warning("No entries found in CNN RSS feed")
                return []

            # Calculate cutoff time
            cutoff_time = datetime.now(UTC) - timedelta(hours=self.hours_back)

            articles = []
            for entry in feed.entries:
                # Stop if we've reached the limit
                if len(articles) >= self.limit:
                    break

                try:
                    # Parse publication date
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(
                            *entry.published_parsed[:6], tzinfo=UTC
                        )

                    # Skip articles older than cutoff
                    if published_at and published_at < cutoff_time:
                        logger.debug(
                            f"Skipping old article: {entry.title} ({published_at})"
                        )
                        continue

                    # Extract article data
                    article = {
                        "title": (
                            entry.title.strip()
                            if hasattr(entry, "title")
                            else "No Title"
                        ),
                        "source": "CNN",
                        "url": entry.link.strip() if hasattr(entry, "link") else "",
                        "raw_text": (
                            entry.summary.strip()
                            if hasattr(entry, "summary")
                            else "No content available"
                        ),
                        "published_at": published_at or datetime.now(UTC),
                    }

                    # Skip if no URL
                    if not article["url"]:
                        continue

                    articles.append(article)
                    logger.debug(f"Added article: {article['title']}")

                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} recent CNN articles")
            return articles

        except Exception as e:
            logger.error(f"Error fetching CNN RSS feed: {e}")
            return []

    async def fetch_newsapi_headlines(self) -> list[dict]:
        """Fetch top headlines from NewsAPI for US in English"""
        logger.info(f"Fetching NewsAPI headlines, limit {self.limit}")

        try:
            # Get API key from environment
            api_key = os.getenv("NEWSCLIENT_API_KEY")
            if not api_key:
                logger.error("NEWSCLIENT_API_KEY environment variable not set")
                return []

            # Initialize NewsAPI client
            newsapi = NewsApiClient(api_key=api_key)

            # Rate limiting - be respectful to API
            await asyncio.sleep(1.0)

            # Fetch top headlines for US in English
            logger.debug(f"Fetching US headlines with limit {self.limit}")
            response = newsapi.get_top_headlines(
                country="us",
                language="en",
                page_size=min(self.limit, 100),  # API max is 100
            )

            if response["status"] != "ok":
                logger.error(
                    f"NewsAPI error: {response.get('message', 'Unknown error')}"
                )
                return []

            articles_data = response.get("articles", [])
            logger.debug(f"NewsAPI returned {len(articles_data)} articles")

            if not articles_data:
                logger.warning("No articles returned from NewsAPI")
                return []

            # Transform articles to our format
            articles = []
            for article_data in articles_data:
                try:
                    # Parse publication date
                    published_at = None
                    if article_data.get("publishedAt"):
                        # NewsAPI returns ISO format: "2023-12-01T10:30:00Z"
                        published_at = datetime.fromisoformat(
                            article_data["publishedAt"].replace("Z", "+00:00")
                        )

                    # Map to our article format
                    article = {
                        "title": article_data.get("title", "No Title").strip(),
                        "source": article_data.get("source", {}).get("name", "NewsAPI"),
                        "url": article_data.get("url", "").strip(),
                        "raw_text": article_data.get(
                            "description", "No description available"
                        ).strip(),
                        "published_at": published_at or datetime.now(UTC),
                    }

                    # Skip if no URL
                    if not article["url"]:
                        logger.debug("Skipping article with no URL")
                        continue

                    articles.append(article)
                    logger.debug(f"Added NewsAPI article: {article['title']}")

                except Exception as e:
                    logger.error(f"Error parsing NewsAPI article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} NewsAPI headlines")
            return articles

        except Exception as e:
            logger.error(f"Error fetching NewsAPI headlines: {e}")
            return []

    def is_duplicate(self, db: Session, article: dict) -> bool:
        """Check if article already exists"""
        # Check by URL in database
        existing = db.query(Article).filter(Article.url == article["url"]).first()
        if existing:
            return True

        # Check in memory
        if article["url"] in self.processed_urls:
            return True

        return False

    def store_article(self, db: Session, article: dict) -> int | None:
        """Store single article in database and return article_id"""
        try:
            # Handle None publication date with fallback
            published_at = (
                article["published_at"]
                if article["published_at"]
                else datetime.now(UTC)
            )

            new_article = Article(
                title=article["title"],
                source=article["source"],
                url=article["url"],
                published_at=published_at,
                raw_text=article["raw_text"],
                created_at=datetime.now(UTC),
            )

            db.add(new_article)
            db.commit()
            db.refresh(new_article)  # Refresh to get the article_id
            self.processed_urls.add(article["url"])

            logger.info(f"Stored: {article['title']} (ID: {new_article.article_id})")
            return new_article.article_id

        except Exception as e:
            logger.error(f"Error storing article: {e}")
            db.rollback()
            return None

    def generate_article_summary(self, db: Session, article_id: int, raw_text: str) -> bool:
        """Generate and store a summary for an article"""
        try:
            if not raw_text or len(raw_text.strip()) < 50:
                logger.debug(f"Article {article_id} text too short for summarization")
                return False

            logger.info(f"🔄 Generating summary for article {article_id}")
            
            summary_text = summarize_with_gemini(raw_text)
            
            if not summary_text:
                logger.warning(f"Empty summary returned for article {article_id}")
                return False

            new_summary = Summary(
                article_id=article_id,
                summary_text=summary_text,
            )
            db.add(new_summary)
            db.commit()

            logger.info(f"✅ Summary generated for article {article_id}: {summary_text[:80]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Error generating summary for article {article_id}: {e}")
            db.rollback()
            return False

    async def analyze_article_bias(self, db: Session, article_id: int, raw_text: str) -> bool:
        """Analyze bias for an article and store the rating (legacy + SECM)"""
        import json
        
        try:
            if not raw_text or len(raw_text.strip()) < 50:
                logger.debug(f"Article {article_id} text too short for bias analysis")
                return False

            logger.info(f"🔄 Analyzing bias for article {article_id} (legacy + SECM)")
            
            # Legacy 4-dimension analysis
            bias_result = await rate_bias(raw_text)

            # Extract scores from result
            scores = bias_result.get("scores", {})

            # Extract individual dimension scores (on 1-7 scale)
            partisan_bias = scores.get("partisan_bias")
            affective_bias = scores.get("affective_bias")
            framing_bias = scores.get("framing_bias")
            sourcing_bias = scores.get("sourcing_bias")

            # Calculate overall bias score as average of dimensions, then normalize to -1 to 1
            valid_scores = [s for s in [partisan_bias, affective_bias, framing_bias, sourcing_bias] if s is not None]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                overall_bias_score = normalize_score_to_range(avg_score)  # Convert 1-7 to -1 to 1
            else:
                overall_bias_score = None

            # SECM analysis (22 parallel LLM calls with K=4 smoothing)
            logger.info(f"🔄 Running SECM analysis for article {article_id} (22 LLM calls)")
            try:
                secm_result = await rate_secm(raw_text)
                secm_ideological = secm_result.get("ideological_score")
                secm_epistemic = secm_result.get("epistemic_score")
                secm_variables = secm_result.get("variables", {})
                secm_reasoning = secm_result.get("reasoning", {})
                logger.info(f"✅ SECM analysis complete for article {article_id}: ideological={secm_ideological}, epistemic={secm_epistemic}")
            except Exception as e:
                logger.error(f"❌ SECM analysis failed for article {article_id}: {e}")
                secm_ideological = None
                secm_epistemic = None
                secm_variables = {}
                secm_reasoning = {}

            # Check if bias rating already exists (might need SECM update)
            existing_rating = db.query(BiasRating).filter(BiasRating.article_id == article_id).first()
            
            if existing_rating:
                # Update existing rating with SECM scores
                existing_rating.secm_ideological_score = secm_ideological
                existing_rating.secm_epistemic_score = secm_epistemic
                existing_rating.secm_ideol_l1_systemic_naming = secm_variables.get("secm_ideol_l1_systemic_naming")
                existing_rating.secm_ideol_l2_power_gap_lexicon = secm_variables.get("secm_ideol_l2_power_gap_lexicon")
                existing_rating.secm_ideol_l3_elite_culpability = secm_variables.get("secm_ideol_l3_elite_culpability")
                existing_rating.secm_ideol_l4_resource_redistribution = secm_variables.get("secm_ideol_l4_resource_redistribution")
                existing_rating.secm_ideol_l5_change_as_justice = secm_variables.get("secm_ideol_l5_change_as_justice")
                existing_rating.secm_ideol_l6_care_harm = secm_variables.get("secm_ideol_l6_care_harm")
                existing_rating.secm_ideol_r1_agentic_culpability = secm_variables.get("secm_ideol_r1_agentic_culpability")
                existing_rating.secm_ideol_r2_order_lexicon = secm_variables.get("secm_ideol_r2_order_lexicon")
                existing_rating.secm_ideol_r3_institutional_defense = secm_variables.get("secm_ideol_r3_institutional_defense")
                existing_rating.secm_ideol_r4_meritocratic_defense = secm_variables.get("secm_ideol_r4_meritocratic_defense")
                existing_rating.secm_ideol_r5_change_as_threat = secm_variables.get("secm_ideol_r5_change_as_threat")
                existing_rating.secm_ideol_r6_sanctity_degradation = secm_variables.get("secm_ideol_r6_sanctity_degradation")
                existing_rating.secm_epist_h1_primary_documentation = secm_variables.get("secm_epist_h1_primary_documentation")
                existing_rating.secm_epist_h2_adversarial_sourcing = secm_variables.get("secm_epist_h2_adversarial_sourcing")
                existing_rating.secm_epist_h3_specific_attribution = secm_variables.get("secm_epist_h3_specific_attribution")
                existing_rating.secm_epist_h4_data_contextualization = secm_variables.get("secm_epist_h4_data_contextualization")
                existing_rating.secm_epist_h5_methodological_transparency = secm_variables.get("secm_epist_h5_methodological_transparency")
                existing_rating.secm_epist_e1_emotive_adjectives = secm_variables.get("secm_epist_e1_emotive_adjectives")
                existing_rating.secm_epist_e2_labeling_othering = secm_variables.get("secm_epist_e2_labeling_othering")
                existing_rating.secm_epist_e3_causal_certainty = secm_variables.get("secm_epist_e3_causal_certainty")
                existing_rating.secm_epist_e4_imperative_direct_address = secm_variables.get("secm_epist_e4_imperative_direct_address")
                existing_rating.secm_epist_e5_motivated_reasoning = secm_variables.get("secm_epist_e5_motivated_reasoning")
                existing_rating.secm_reasoning_json = json.dumps(secm_reasoning) if secm_reasoning else None
                existing_rating.evaluated_at = datetime.now(UTC)
                db.commit()
            else:
                # Create new rating
                new_rating = BiasRating(
                    article_id=article_id,
                    bias_score=overall_bias_score,
                    partisan_bias=partisan_bias,
                    affective_bias=affective_bias,
                    framing_bias=framing_bias,
                    sourcing_bias=sourcing_bias,
                    reasoning=None,
                    evaluated_at=datetime.now(UTC),
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

            secm_str = f", SECM ideo={secm_ideological:+.2f}" if secm_ideological is not None else " (SECM failed)"
            logger.info(
                f"✅ Bias rating stored for article {article_id}: "
                f"overall={overall_bias_score}{secm_str}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error analyzing bias for article {article_id}: {e}")
            db.rollback()
            return False

    async def process_articles(self, articles: list[dict], run_llm: bool = True) -> int:
        """Process and store articles, optionally with LLM analysis"""
        if not articles:
            return 0

        logger.info(f"📥 Processing {len(articles)} articles (LLM: {run_llm})...")

        with get_connection() as db:
            stored_count = 0
            summary_count = 0
            bias_count = 0

            try:
                for i, article in enumerate(articles, 1):
                    if not self.is_duplicate(db, article):
                        article_id = self.store_article(db, article)
                        if article_id:
                            stored_count += 1
                            
                            if run_llm:
                                raw_text = article.get("raw_text", "")
                                logger.info(f"📰 [{i}/{len(articles)}] Processing article {article_id}: {article['title'][:50]}...")
                                
                                # Generate summary
                                if self.generate_article_summary(db, article_id, raw_text):
                                    summary_count += 1
                                
                                # Analyze bias (legacy + SECM)
                                if await self.analyze_article_bias(db, article_id, raw_text):
                                    bias_count += 1
                    else:
                        logger.debug(f"Duplicate skipped: {article['title']}")
            except Exception as e:
                logger.error(f"❌ Error processing articles: {e}")

        if run_llm:
            logger.info(f"✅ Processing complete: {stored_count} stored, {summary_count} summaries, {bias_count} bias ratings")
        else:
            logger.info(f"✅ Processing complete: {stored_count} stored (LLM skipped)")

        # Prevent memory leak by cleaning up old URLs
        self.cleanup_memory()

        return stored_count

    async def backfill_missing_analysis(self, limit: int = 20) -> tuple[int, int]:
        """Backfill summaries and bias ratings for articles missing them"""
        from sqlalchemy import and_, or_
        from sqlalchemy.orm import Session
        
        summary_count = 0
        bias_count = 0
        
        with get_connection() as db:
            # Find articles missing bias ratings OR missing SECM scores
            articles_missing_bias = (
                db.query(Article)
                .outerjoin(BiasRating, Article.article_id == BiasRating.article_id)
                .filter(or_(
                    BiasRating.rating_id == None,
                    BiasRating.secm_ideological_score == None,
                    BiasRating.secm_epistemic_score == None
                ))
                .limit(limit)
                .all()
            )
            
            if articles_missing_bias:
                logger.info(f"🔧 Backfilling {len(articles_missing_bias)} articles missing analysis or SECM scores...")
                
                for article in articles_missing_bias:
                    # Check if summary exists
                    has_summary = db.query(Summary).filter(Summary.article_id == article.article_id).first()
                    
                    if not has_summary and article.raw_text:
                        if self.generate_article_summary(db, article.article_id, article.raw_text):
                            summary_count += 1
                    
                    # Run bias analysis
                    if article.raw_text:
                        if await self.analyze_article_bias(db, article.article_id, article.raw_text):
                            bias_count += 1
                
                logger.info(f"✅ Backfill complete: {summary_count} summaries, {bias_count} bias ratings added")
            else:
                logger.debug("No articles missing bias ratings")
        
        return summary_count, bias_count

    async def run_single_fetch(
        self, use_cnn: bool = False, use_newsapi: bool = False, use_stub: bool = False, run_llm: bool = True
    ) -> int:
        """Run one fetch cycle"""
        if use_newsapi:
            logger.info("Running single fetch with NewsAPI")
            articles = await self.fetch_newsapi_headlines()
        elif use_cnn:
            logger.info("Running single fetch with CNN scraper")
            articles = await self.fetch_cnn_articles()
        elif use_stub:
            logger.info("Running single fetch with stubbed articles (testing only)")
            articles = await self.fetch_stubbed_articles()
        else:
            logger.info("Running single fetch with RSS feeds")
            articles = await self.fetch_rss_articles()

        return await self.process_articles(articles, run_llm=run_llm)

    async def run_scheduler(self):
        """Run continuous scheduler"""
        logger.info(f"Starting scheduler (interval: {POLL_INTERVAL}s)")
        self.running = True

        while self.running:
            try:
                stored_count = await self.run_single_fetch()
                logger.info(f"Fetch cycle complete: {stored_count} articles stored")

                # Wait for next cycle
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        logger.info("Scheduler stopped")

    def stop(self):
        """Stop the scheduler"""
        self.running = False

    def show_status(self):
        """Show current status"""
        with get_connection() as db:
            try:
                total_articles = db.query(Article).count()

                recent = (
                    db.query(Article.title, Article.source, Article.created_at)
                    .order_by(Article.created_at.desc())
                    .limit(5)
                    .all()
                )

                logger.info("=== Status ===")
                logger.info(f"Total articles: {total_articles}")
                logger.info(f"Running: {self.running}")

                if recent:
                    logger.info("Recent articles:")
                    for title, source, created_at in recent:
                        logger.info(f"  - {title} ({source})")
            except Exception as e:
                logger.error(f"Error showing status: {e}")

    def show_all_articles(self):
        """Show all articles with details"""
        with get_connection() as db:
            try:
                articles = (
                    db.query(
                        Article.article_id,
                        Article.title,
                        Article.source,
                        Article.url,
                        Article.created_at,
                    )
                    .order_by(Article.created_at.desc())
                    .all()
                )

                print(f"\n=== ALL ARTICLES ({len(articles)} total) ===")
                for article_id, title, source, url, created_at in articles:
                    print(f"ID: {article_id}")
                    print(f"Title: {title}")
                    print(f"Source: {source}")
                    print(f"URL: {url}")
                    print(f"Created: {created_at}")
                    print("-" * 50)
            except Exception as e:
                logger.error(f"Error showing articles: {e}")

    def show_sources_summary(self):
        """Show summary by source"""
        with get_connection() as db:
            try:
                from sqlalchemy import func

                sources = (
                    db.query(
                        Article.source,
                        func.count(Article.article_id).label("count"),
                        func.max(Article.created_at).label("latest"),
                    )
                    .group_by(Article.source)
                    .order_by(func.count(Article.article_id).desc())
                    .all()
                )

                print("\n=== SOURCES SUMMARY ===")
                for source, count, latest in sources:
                    print(f"{source}: {count} articles (latest: {latest})")
            except Exception as e:
                logger.error(f"Error showing sources summary: {e}")

    def clear_database(self):
        """Clear all articles (for testing)"""
        with get_connection() as db:
            try:
                db.query(Article).delete()
                db.commit()
                self.processed_urls.clear()
                logger.info("Database cleared")
            except Exception as e:
                logger.error(f"Error clearing database: {e}")
                db.rollback()

    def cleanup_memory(self, max_urls: int = 1000):
        """Clean up processed_urls to prevent memory leak"""
        if len(self.processed_urls) > max_urls:
            # Keep only the most recent half
            urls_to_keep = list(self.processed_urls)[-max_urls // 2 :]
            self.processed_urls = set(urls_to_keep)
            logger.info(f"Cleaned up processed URLs, kept {len(self.processed_urls)}")


async def main():
    """Main entry point"""
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    parser = argparse.ArgumentParser(description="News Worker")
    parser.add_argument("--once", action="store_true", help="Run single fetch")
    parser.add_argument(
        "--cnn", action="store_true", help="Use CNN scraper instead of stubs"
    )
    parser.add_argument(
        "--newsapi", action="store_true", help="Use NewsAPI for headlines"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=DEFAULT_HOURS_BACK,
        help=f"Hours back to fetch (default: {DEFAULT_HOURS_BACK})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_ARTICLE_LIMIT,
        help=f"Max articles to fetch (default: {DEFAULT_ARTICLE_LIMIT})",
    )
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--show-all", action="store_true", help="Show all articles")
    parser.add_argument("--sources", action="store_true", help="Show sources summary")
    parser.add_argument("--clear", action="store_true", help="Clear database")

    args = parser.parse_args()

    # Setup logging
    logger.remove()
    log_level = "DEBUG" if args.cnn else "INFO"  # More verbose for CNN debugging
    logger.add(sys.stderr, level=log_level, format="{time} | {level} | {message}")

    # Initialize database
    init_db()

    worker = NewsWorker(hours_back=args.hours, limit=args.limit)

    try:
        if args.status:
            worker.show_status()
        elif args.show_all:
            worker.show_all_articles()
        elif args.sources:
            worker.show_sources_summary()
        elif args.clear:
            worker.clear_database()
        elif args.once:
            count = await worker.run_single_fetch(
                use_cnn=args.cnn, use_newsapi=args.newsapi
            )
            logger.info(f"Single fetch complete: {count} articles stored")
        else:
            await worker.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
