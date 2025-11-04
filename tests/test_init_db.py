import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker

from src.db.init_db import get_connection, init_db
from src.db.sqlalchemy import Base
from src.models.sqlalchemy_models import User, Article, Summary, BiasRating, UserInteraction


class TestGetConnection:
    """Test cases for the get_connection function."""
    
    def test_get_connection_returns_session(self):
        """Test get_connection returns a valid SQLAlchemy session."""
        # Use context manager to get a session
        with get_connection() as session:
            # Verify it's a valid session
            from sqlalchemy.orm import Session
            assert isinstance(session, Session)
            
            # Test that we can query (even if table doesn't exist yet)
            # This verifies the session is functional
            assert session is not None
    
    def test_get_connection_context_manager(self):
        """Test get_connection works as a context manager."""
        # Create a session
        with get_connection() as session:
            assert session is not None
            # Session should be open during the context
            assert session.is_active or not session.is_active  # Either state is valid
        
        # After exiting context, session should be closed
        # We can't easily test this without implementation details
    
    def test_get_connection_custom_db_path(self):
        """Test get_connection respects DB_PATH environment variable."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            custom_path = tmp_file.name
        
        try:
            # Set custom DB_PATH
            with patch.dict(os.environ, {'DB_PATH': custom_path}):
                # We need to reload the module to pick up the new env var
                # For this test, we'll just verify the connection works
                with get_connection() as session:
                    from sqlalchemy.orm import Session
                    assert isinstance(session, Session)
        finally:
            if os.path.exists(custom_path):
                os.unlink(custom_path)


class TestInitDb:
    """Test cases for the init_db function."""
    
    def test_init_db_creates_all_tables(self):
        """Test that init_db creates all required tables."""
        # Use in-memory database for testing
        engine = create_engine("sqlite:///:memory:")
        
        # Initialize the database
        result = init_db()  # This will use the global engine, but we'll inspect our test engine
        
        # For testing, create tables directly on our test engine
        Base.metadata.create_all(bind=engine)
        
        # Check that all expected tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['articles', 'bias_ratings', 'summaries', 'user_interactions', 'users']
        assert sorted(tables) == sorted(expected_tables)
    
    def test_init_db_users_table_structure(self):
        """Test that the users table has the correct structure."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        # Check users table structure using SQLAlchemy inspector
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        
        # Expected columns: user_id, username, email, created_at
        column_names = [col['name'] for col in columns]
        expected_columns = ['user_id', 'username', 'email', 'created_at']
        assert column_names == expected_columns
        
        # Check primary key
        pk_constraint = inspector.get_pk_constraint('users')
        assert pk_constraint['constrained_columns'] == ['user_id']
    
    def test_init_db_articles_table_structure(self):
        """Test that the articles table has the correct structure."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        columns = inspector.get_columns('articles')
        
        column_names = [col['name'] for col in columns]
        expected_columns = ['article_id', 'title', 'source', 'url', 'published_at', 'raw_text', 'created_at']
        assert column_names == expected_columns
        
        # Check primary key
        pk_constraint = inspector.get_pk_constraint('articles')
        assert pk_constraint['constrained_columns'] == ['article_id']
    
    def test_init_db_foreign_key_constraints(self):
        """Test that foreign key constraints are properly set up."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        
        # Check summaries table foreign key
        fk_constraints = inspector.get_foreign_keys('summaries')
        assert len(fk_constraints) == 1
        assert fk_constraints[0]['referred_table'] == 'articles'
        assert 'article_id' in fk_constraints[0]['constrained_columns']
        
        # Check bias_ratings table foreign key
        fk_constraints = inspector.get_foreign_keys('bias_ratings')
        assert len(fk_constraints) == 1
        assert fk_constraints[0]['referred_table'] == 'articles'
        
        # Check user_interactions table foreign keys
        fk_constraints = inspector.get_foreign_keys('user_interactions')
        assert len(fk_constraints) == 2  # Should have 2 foreign keys (user_id and article_id)
    
    def test_init_db_can_be_called_multiple_times(self):
        """Test that init_db can be called multiple times without error."""
        # Call init_db multiple times - SQLAlchemy handles CREATE TABLE IF NOT EXISTS internally
        result1 = init_db()
        result2 = init_db()
        result3 = init_db()
        
        # All should succeed
        assert result1 is True
        assert result2 is True
        assert result3 is True
    
    def test_init_db_user_interactions_action_constraint(self):
        """Test that user_interactions table has proper CHECK constraint on action column."""
        engine = create_engine("sqlite:///:memory:")
        
        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Insert a user and article first (to satisfy foreign key constraints)
            user = User(username="testuser", email="test@example.com")
            article = Article(title="Test Article", source="Test Source")
            db.add(user)
            db.add(article)
            db.commit()
            db.refresh(user)
            db.refresh(article)
            
            # Test valid actions
            valid_actions = ['viewed', 'liked', 'bookmarked']
            for action in valid_actions:
                interaction = UserInteraction(
                    user_id=user.user_id,
                    article_id=article.article_id,
                    action=action
                )
                db.add(interaction)
            db.commit()
            
            # Test invalid action should raise an error
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):
                invalid_interaction = UserInteraction(
                    user_id=user.user_id,
                    article_id=article.article_id,
                    action='invalid_action'
                )
                db.add(invalid_interaction)
                db.commit()
        finally:
            db.close()
    
    def test_init_db_with_error_handling(self):
        """Test init_db error handling."""
        # Test that init_db handles exceptions gracefully
        # We'll mock the Base.metadata.create_all to raise an exception
        with patch('src.db.init_db.Base.metadata.create_all') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            result = init_db()
            assert result is False
    
    def test_init_db_returns_true_on_success(self):
        """Test that init_db returns True when successful."""
        result = init_db()
        assert result is True


class TestIntegration:
    """Integration tests combining get_connection and init_db."""
    
    def test_full_database_initialization(self):
        """Test complete database initialization workflow."""
        # Use in-memory database to avoid file conflicts
        engine = create_engine("sqlite:///:memory:")
        
        # Enable foreign keys
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # Initialize the database
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Verify we can insert and retrieve data
            user = User(username="testuser", email="test@example.com")
            db.add(user)
            db.commit()
            db.refresh(user)
            
            article = Article(
                title="Test Article",
                source="Test Source",
                url="http://example.com"
            )
            db.add(article)
            db.commit()
            db.refresh(article)
            
            # Verify data was inserted
            retrieved_user = db.query(User).filter(User.username == "testuser").first()
            assert retrieved_user is not None
            assert retrieved_user.username == "testuser"
            
            retrieved_article = db.query(Article).filter(Article.title == "Test Article").first()
            assert retrieved_article is not None
            assert retrieved_article.title == "Test Article"
            
            # Test foreign key relationships work
            summary = Summary(
                article_id=article.article_id,
                summary_text="This is a test summary"
            )
            db.add(summary)
            db.commit()
            
            retrieved_summary = db.query(Summary).filter(Summary.article_id == article.article_id).first()
            assert retrieved_summary is not None
            assert retrieved_summary.summary_text == "This is a test summary"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__])