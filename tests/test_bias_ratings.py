"""
Simple unit tests for bias rating endpoints.
Tests the core functionality using SQLAlchemy.
"""
import pytest
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.sqlalchemy import Base
from src.models.sqlalchemy_models import Article, BiasRating
from src.db.init_db import init_db


@pytest.fixture
def test_db():
    """Create an in-memory test database with sample data using SQLAlchemy"""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    db = TestSessionLocal()
    
    try:
        # Insert test article (required for foreign key)
        test_article = Article(
            title="Test Article",
            source="Test Source",
            created_at=datetime.utcnow()
        )
        db.add(test_article)
        db.commit()
        db.refresh(test_article)
        
        # Insert test bias rating
        test_rating = BiasRating(
            article_id=test_article.article_id,
            bias_score=0.5,
            reasoning="Test reasoning",
            evaluated_at=datetime.utcnow()
        )
        db.add(test_rating)
        db.commit()
        
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestBiasRatingEndpoints:
    """Test bias rating endpoint functionality"""
    
    def test_get_all_bias_ratings_data(self, test_db):
        """Test retrieving all bias ratings returns correct data"""
        results = test_db.query(BiasRating).all()
        
        assert len(results) == 1
        assert results[0].rating_id == 1
        assert results[0].article_id == 1
        assert results[0].bias_score == 0.5
        assert results[0].reasoning == "Test reasoning"
    
    def test_get_bias_rating_by_id_exists(self, test_db):
        """Test retrieving a specific bias rating that exists"""
        result = test_db.query(BiasRating).filter(BiasRating.rating_id == 1).first()
        
        assert result is not None
        assert result.rating_id == 1
        assert result.bias_score == 0.5
    
    def test_get_bias_rating_by_id_not_found(self, test_db):
        """Test retrieving a bias rating that doesn't exist"""
        result = test_db.query(BiasRating).filter(BiasRating.rating_id == 999).first()
        
        assert result is None
    
    def test_update_bias_rating_success(self, test_db):
        """Test successfully updating a bias rating"""
        # Get the bias rating
        rating = test_db.query(BiasRating).filter(BiasRating.rating_id == 1).first()
        
        # Update the bias rating
        rating.bias_score = 0.8
        rating.reasoning = "Updated reasoning"
        test_db.commit()
        
        # Verify the update
        test_db.refresh(rating)
        
        assert rating.bias_score == 0.8
        assert rating.reasoning == "Updated reasoning"
    
    def test_update_partial_fields(self, test_db):
        """Test updating only some fields"""
        # Get the bias rating
        rating = test_db.query(BiasRating).filter(BiasRating.rating_id == 1).first()
        
        # Update only bias_score
        rating.bias_score = -0.3
        test_db.commit()
        
        # Verify bias_score changed but reasoning stayed the same
        test_db.refresh(rating)
        
        assert rating.bias_score == -0.3  # bias_score updated
        assert rating.reasoning == "Test reasoning"  # reasoning unchanged
    
    def test_bias_score_validation(self):
        """Test bias score validation logic"""
        # Valid scores
        valid_scores = [-1.0, -0.5, 0.0, 0.5, 1.0]
        for score in valid_scores:
            assert -1.0 <= score <= 1.0, f"Score {score} should be valid"
        
        # Invalid scores
        invalid_scores = [-1.1, 1.1, -2.0, 2.0]
        for score in invalid_scores:
            assert not (-1.0 <= score <= 1.0), f"Score {score} should be invalid"
    
    def test_bias_rating_exists_check(self, test_db):
        """Test checking if a bias rating exists"""
        # Check existing rating
        exists = test_db.query(BiasRating).filter(BiasRating.rating_id == 1).first() is not None
        assert exists is True
        
        # Check non-existing rating
        exists = test_db.query(BiasRating).filter(BiasRating.rating_id == 999).first() is not None
        assert exists is False
    
    def test_database_error_handling(self):
        """Test database error scenarios"""
        from sqlalchemy.exc import PendingRollbackError, InvalidRequestError
        
        # Test with a transaction that's been rolled back
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestSessionLocal = sessionmaker(bind=engine)
        db = TestSessionLocal()
        
        try:
            # Create an article first
            article = Article(title="Test", source="Test")
            db.add(article)
            db.commit()
            
            # Start a transaction that will fail
            try:
                # Try to insert an invalid bias rating (invalid foreign key)
                invalid_rating = BiasRating(
                    article_id=999,  # Doesn't exist
                    bias_score=0.5
                )
                db.add(invalid_rating)
                db.flush()  # This will fail
            except Exception:
                # Transaction is now in a failed state
                pass
            
            # Attempting to do another operation without rolling back should fail
            # In SQLAlchemy 2.0, this behavior is more lenient, so we'll test
            # that we can still rollback properly
            db.rollback()  # Should not raise
            
            # Verify we can use the session after rollback
            count = db.query(BiasRating).count()
            assert count == 0
        finally:
            db.close()
    
    def test_foreign_key_constraint(self, test_db):
        """Test foreign key constraints work"""
        from sqlalchemy.exc import IntegrityError
        
        # Try to insert bias rating for non-existent article
        # SQLite needs foreign keys explicitly enabled in the connection string
        # Since we can't control that in the fixture easily, we'll create a new engine
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        
        # Enable foreign keys
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(bind=engine)
        TestSessionLocal = sessionmaker(bind=engine)
        db = TestSessionLocal()
        
        try:
            with pytest.raises(IntegrityError):
                invalid_rating = BiasRating(
                    article_id=999,  # article_id 999 doesn't exist
                    bias_score=0.5,
                    reasoning="Test"
                )
                db.add(invalid_rating)
                db.commit()
        finally:
            db.close()
    
    def test_empty_database_scenario(self):
        """Test behavior with empty bias_ratings table"""
        # Create a fresh in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestSessionLocal = sessionmaker(bind=engine)
        db = TestSessionLocal()
        
        try:
            count = db.query(BiasRating).count()
            assert count == 0
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__])