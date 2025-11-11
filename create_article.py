import os
from datetime import datetime
from src.db.sqlalchemy import SessionLocal, Base, engine
from src.models.sqlalchemy_models import Article

# Initialize database
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Full article text for testing
article_text = """
Climate Change and Economic Impact: A Comprehensive Analysis

Washington, D.C. - Scientists and economists worldwide are increasingly concerned about the economic ramifications of climate change, with a new report suggesting that unchecked greenhouse gas emissions could cost the global economy trillions of dollars by 2050.

The report, released by the International Panel on Climate Change, indicates that rising temperatures will lead to crop failures, coastal flooding, and disruptions to supply chains. "We are seeing the early stages of climate-driven economic disruption," said Dr. Elizabeth Chen, lead author of the study.

Critics argue that aggressive climate policies could harm economic growth. "We need to balance environmental concerns with economic realities," said Senator James Republican, from Texas. "Overregulation will destroy jobs and hurt working families."

Proponents of climate action counter that the cost of inaction far outweighs the cost of transition. "Renewable energy is already cheaper than fossil fuels in most markets," explained Green Energy Coalition Director Michael Torres. "Investing in clean technology creates jobs and economic opportunities."

The debate continues in Congress, with Democratic lawmakers pushing for the Clean Energy Act, while Republican members propose market-based solutions and gradual transitions.

The economic impact remains uncertain, but scientists warn that delays in addressing climate change will only increase future costs.
"""

article = Article(
    title="Climate Change and Economic Impact: A Comprehensive Analysis",
    source="News Wire",
    url="https://newswire.example.com/climate-analysis",
    raw_text=article_text,
    created_at=datetime.utcnow(),
)

db.add(article)
db.commit()
db.refresh(article)

print(f"✅ Article created with ID: {article.article_id}")
print(f"   Title: {article.title}")
print(f"   Text length: {len(article.raw_text)} characters")

db.close()
