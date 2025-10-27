import os
import sqlite3
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from db.init_db import get_connection, init_db


class TestGetConnection:
    """Test cases for the get_connection function."""
    
    def test_get_connection_default_path(self):
        """Test get_connection returns a valid connection with default DB_PATH."""
        # Use a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            temp_db_path = tmp_file.name
        
        try:
            with patch.dict(os.environ, {'DB_PATH': temp_db_path}):
                conn = get_connection()
                
                # Verify it's a valid connection
                assert isinstance(conn, sqlite3.Connection)
                
                # Test that foreign keys are enabled
                cursor = conn.execute("PRAGMA foreign_keys")
                result = cursor.fetchone()
                assert result[0] == 1  # Foreign keys should be ON (1)
                
                conn.close()
        finally:
            # Clean up
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_get_connection_custom_path(self):
        """Test get_connection with custom DB_PATH environment variable."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            custom_path = tmp_file.name
        
        try:
            with patch.dict(os.environ, {'DB_PATH': custom_path}):
                conn = get_connection()
                
                # Verify connection is valid
                assert isinstance(conn, sqlite3.Connection)
                
                # Verify it connects to the correct database
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()  # Should be empty for new database
                assert isinstance(tables, list)
                
                conn.close()
        finally:
            if os.path.exists(custom_path):
                os.unlink(custom_path)
    
    def test_get_connection_no_env_var(self):
        """Test get_connection falls back to default when no DB_PATH env var."""
        # Remove DB_PATH from environment if it exists
        env_copy = os.environ.copy()
        if 'DB_PATH' in os.environ:
            del os.environ['DB_PATH']
        
        try:
            # Mock sqlite3.connect to avoid creating actual file
            with patch('db.init_db.sqlite3.connect') as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn
                
                conn = get_connection()
                
                # Verify it uses the default path
                mock_connect.assert_called_once_with("veritas_news.db", check_same_thread=False)
                mock_conn.execute.assert_called_once_with("PRAGMA foreign_keys = ON;")
                
                assert conn == mock_conn
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(env_copy)


class TestInitDb:
    """Test cases for the init_db function."""
    
    def test_init_db_creates_all_tables(self):
        """Test that init_db creates all required tables."""
        # Use in-memory database for testing
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Initialize the database
        init_db(conn)
        
        # Check that all expected tables were created (excluding system tables)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['articles', 'bias_ratings', 'summaries', 'user_interactions', 'users']
        assert sorted(tables) == sorted(expected_tables)
        
        conn.close()
    
    def test_init_db_users_table_structure(self):
        """Test that the users table has the correct structure."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        
        # Check users table structure
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        # Expected columns: user_id, username, email, created_at
        column_names = [col[1] for col in columns]
        expected_columns = ['user_id', 'username', 'email', 'created_at']
        assert column_names == expected_columns
        
        # Check primary key and constraints
        primary_key_col = [col for col in columns if col[5] == 1]  # pk column
        assert len(primary_key_col) == 1
        assert primary_key_col[0][1] == 'user_id'
        
        conn.close()
    
    def test_init_db_articles_table_structure(self):
        """Test that the articles table has the correct structure."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        
        cursor = conn.execute("PRAGMA table_info(articles)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        expected_columns = ['article_id', 'title', 'source', 'url', 'published_at', 'raw_text', 'created_at']
        assert column_names == expected_columns
        
        # Check primary key
        primary_key_col = [col for col in columns if col[5] == 1]
        assert len(primary_key_col) == 1
        assert primary_key_col[0][1] == 'article_id'
        
        conn.close()
    
    def test_init_db_foreign_key_constraints(self):
        """Test that foreign key constraints are properly set up."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        
        # Check summaries table foreign key
        cursor = conn.execute("PRAGMA foreign_key_list(summaries)")
        fk_info = cursor.fetchall()
        assert len(fk_info) == 1
        assert fk_info[0][2] == 'articles'  # references articles table
        assert fk_info[0][3] == 'article_id'  # references article_id column
        
        # Check bias_ratings table foreign key
        cursor = conn.execute("PRAGMA foreign_key_list(bias_ratings)")
        fk_info = cursor.fetchall()
        assert len(fk_info) == 1
        assert fk_info[0][2] == 'articles'
        
        # Check user_interactions table foreign keys
        cursor = conn.execute("PRAGMA foreign_key_list(user_interactions)")
        fk_info = cursor.fetchall()
        assert len(fk_info) == 2  # Should have 2 foreign keys
        
        conn.close()
    
    def test_init_db_can_be_called_multiple_times(self):
        """Test that init_db can be called multiple times without error (CREATE TABLE IF NOT EXISTS)."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Call init_db multiple times
        init_db(conn)
        init_db(conn)  # Should not raise an error
        init_db(conn)  # Should not raise an error
        
        # Verify tables still exist and structure is intact (excluding system tables)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['articles', 'bias_ratings', 'summaries', 'user_interactions', 'users']
        assert sorted(tables) == sorted(expected_tables)
        
        conn.close()
    
    def test_init_db_user_interactions_action_constraint(self):
        """Test that user_interactions table has proper CHECK constraint on action column."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        
        # Insert a user and article first (to satisfy foreign key constraints)
        conn.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("testuser", "test@example.com"))
        conn.execute("INSERT INTO articles (title, source) VALUES (?, ?)", ("Test Article", "Test Source"))
        
        # Test valid actions
        valid_actions = ['viewed', 'liked', 'bookmarked']
        for action in valid_actions:
            conn.execute("""
                INSERT INTO user_interactions (user_id, article_id, action) 
                VALUES (1, 1, ?)
            """, (action,))
        
        # Test invalid action should raise an error
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO user_interactions (user_id, article_id, action) 
                VALUES (1, 1, 'invalid_action')
            """)
        
        conn.close()
    
    def test_init_db_with_connection_error(self):
        """Test init_db behavior when connection has issues."""
        # Create a mock connection that will fail
        mock_conn = MagicMock()
        mock_conn.executescript.side_effect = sqlite3.Error("Database error")
        
        # Should return False and call rollback
        result = init_db(mock_conn)
        assert result is False
        mock_conn.rollback.assert_called_once()
    
    def test_init_db_returns_true_on_success(self):
        """Test that init_db returns True when successful."""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        result = init_db(conn)
        assert result is True
        
        conn.close()


class TestIntegration:
    """Integration tests combining get_connection and init_db."""
    
    def test_full_database_initialization(self):
        """Test complete database initialization workflow."""
        # Use in-memory database to avoid file conflicts
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Initialize the database
        init_db(conn)
        
        # Verify we can insert and retrieve data
        conn.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                   ("testuser", "test@example.com"))
        conn.execute("INSERT INTO articles (title, source, url) VALUES (?, ?, ?)", 
                   ("Test Article", "Test Source", "http://example.com"))
        conn.commit()
        
        # Verify data was inserted
        cursor = conn.execute("SELECT username FROM users WHERE username = ?", ("testuser",))
        result = cursor.fetchone()
        assert result[0] == "testuser"
        
        cursor = conn.execute("SELECT title FROM articles WHERE title = ?", ("Test Article",))
        result = cursor.fetchone()
        assert result[0] == "Test Article"
        
        # Test foreign key relationships work
        conn.execute("INSERT INTO summaries (article_id, summary_text) VALUES (?, ?)",
                   (1, "This is a test summary"))
        
        cursor = conn.execute("SELECT summary_text FROM summaries WHERE article_id = ?", (1,))
        result = cursor.fetchone()
        assert result[0] == "This is a test summary"
        
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__])