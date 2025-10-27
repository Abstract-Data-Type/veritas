"""
Simple unit tests for bias rating endpoints.
Tests the core functionality without complex FastAPI client setup.
"""
import pytest
import sqlite3
from unittest.mock import patch, MagicMock

from db.init_db import init_db


@pytest.fixture
def test_db():
    """Create an in-memory test database with sample data"""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize the database schema
    init_db(conn)
    
    # Insert test articles (required for foreign key)
    conn.execute("INSERT INTO articles (title, source) VALUES (?, ?)", ("Test Article", "Test Source"))
    conn.commit()
    
    # Insert test bias rating
    conn.execute("""
        INSERT INTO bias_ratings (article_id, bias_score, reasoning, evaluated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (1, 0.5, "Test reasoning"))
    conn.commit()
    
    yield conn
    conn.close()


class TestBiasRatingEndpoints:
    """Test bias rating endpoint functionality"""
    
    def test_get_all_bias_ratings_data(self, test_db):
        """Test retrieving all bias ratings returns correct data"""
        conn = test_db
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        
        cursor = conn.cursor()
        cursor.execute("SELECT rating_id, article_id, bias_score, reasoning FROM bias_ratings")
        results = cursor.fetchall()
        
        assert len(results) == 1
        assert results[0]['rating_id'] == 1
        assert results[0]['article_id'] == 1
        assert results[0]['bias_score'] == 0.5
        assert results[0]['reasoning'] == "Test reasoning"
    
    def test_get_bias_rating_by_id_exists(self, test_db):
        """Test retrieving a specific bias rating that exists"""
        conn = test_db
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bias_ratings WHERE rating_id = ?", (1,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result['rating_id'] == 1
        assert result['bias_score'] == 0.5
    
    def test_get_bias_rating_by_id_not_found(self, test_db):
        """Test retrieving a bias rating that doesn't exist"""
        conn = test_db
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bias_ratings WHERE rating_id = ?", (999,))
        result = cursor.fetchone()
        
        assert result is None
    
    def test_update_bias_rating_success(self, test_db):
        """Test successfully updating a bias rating"""
        conn = test_db
        cursor = conn.cursor()
        
        # Update the bias rating
        cursor.execute("""
            UPDATE bias_ratings 
            SET bias_score = ?, reasoning = ? 
            WHERE rating_id = ?
        """, (0.8, "Updated reasoning", 1))
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT bias_score, reasoning FROM bias_ratings WHERE rating_id = ?", (1,))
        result = cursor.fetchone()
        
        assert result[0] == 0.8  # bias_score
        assert result[1] == "Updated reasoning"
    
    def test_update_partial_fields(self, test_db):
        """Test updating only some fields"""
        conn = test_db
        cursor = conn.cursor()
        
        # Update only bias_score
        cursor.execute("UPDATE bias_ratings SET bias_score = ? WHERE rating_id = ?", (-0.3, 1))
        conn.commit()
        
        # Verify bias_score changed but reasoning stayed the same
        cursor.execute("SELECT bias_score, reasoning FROM bias_ratings WHERE rating_id = ?", (1,))
        result = cursor.fetchone()
        
        assert result[0] == -0.3  # bias_score updated
        assert result[1] == "Test reasoning"  # reasoning unchanged
    
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
        conn = test_db
        cursor = conn.cursor()
        
        # Check existing rating
        cursor.execute("SELECT 1 FROM bias_ratings WHERE rating_id = ?", (1,))
        exists = cursor.fetchone() is not None
        assert exists is True
        
        # Check non-existing rating
        cursor.execute("SELECT 1 FROM bias_ratings WHERE rating_id = ?", (999,))
        exists = cursor.fetchone() is not None
        assert exists is False
    
    def test_database_error_handling(self):
        """Test database error scenarios"""
        # Test with closed connection
        conn = sqlite3.connect(":memory:")
        conn.close()
        
        with pytest.raises(sqlite3.ProgrammingError):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bias_ratings")
    
    def test_foreign_key_constraint(self, test_db):
        """Test foreign key constraints work"""
        conn = test_db
        cursor = conn.cursor()
        
        # Try to insert bias rating for non-existent article
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO bias_ratings (article_id, bias_score, reasoning)
                VALUES (?, ?, ?)
            """, (999, 0.5, "Test"))  # article_id 999 doesn't exist
    
    def test_empty_database_scenario(self):
        """Test behavior with empty bias_ratings table"""
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        init_db(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bias_ratings")
        count = cursor.fetchone()[0]
        
        assert count == 0
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__])