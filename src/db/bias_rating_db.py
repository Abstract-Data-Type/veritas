import sqlite3
from datetime import datetime
from sqlite3 import Connection, Row
from typing import Any, Dict, List, Optional


def dict_factory(cursor, row):
    """Convert sqlite row to dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_all_bias_ratings(conn: Connection) -> List[Dict[str, Any]]:
    """
    Retrieve all bias ratings from the database

    Args:
        conn: Database connection

    Returns:
        List of bias rating dictionaries
    """
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    query = """
    SELECT 
        rating_id,
        article_id,
        bias_score,
        reasoning,
        evaluated_at
    FROM bias_ratings
    ORDER BY evaluated_at DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    # Convert datetime strings to datetime objects if needed
    for rating in results:
        if rating["evaluated_at"] and isinstance(rating["evaluated_at"], str):
            try:
                rating["evaluated_at"] = datetime.fromisoformat(
                    rating["evaluated_at"].replace("Z", "+00:00")
                )
            except ValueError:
                # Handle different datetime formats
                rating["evaluated_at"] = datetime.strptime(
                    rating["evaluated_at"], "%Y-%m-%d %H:%M:%S"
                )

    return results


def get_bias_rating_by_id(conn: Connection, rating_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single bias rating by ID

    Args:
        conn: Database connection
        rating_id: The ID of the bias rating to retrieve

    Returns:
        Bias rating dictionary or None if not found
    """
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    query = """
    SELECT 
        rating_id,
        article_id,
        bias_score,
        reasoning,
        evaluated_at
    FROM bias_ratings
    WHERE rating_id = ?
    """

    cursor.execute(query, (rating_id,))
    result = cursor.fetchone()

    if result and result["evaluated_at"] and isinstance(result["evaluated_at"], str):
        try:
            result["evaluated_at"] = datetime.fromisoformat(
                result["evaluated_at"].replace("Z", "+00:00")
            )
        except ValueError:
            # Handle different datetime formats
            result["evaluated_at"] = datetime.strptime(
                result["evaluated_at"], "%Y-%m-%d %H:%M:%S"
            )

    return result


def update_bias_rating(
    conn: Connection,
    rating_id: int,
    bias_score: Optional[float] = None,
    reasoning: Optional[str] = None,
) -> bool:
    """
    Update an existing bias rating

    Args:
        conn: Database connection
        rating_id: The ID of the bias rating to update
        bias_score: New bias score (optional)
        reasoning: New reasoning (optional)

    Returns:
        True if update was successful, False if rating not found
    """
    cursor = conn.cursor()

    # Build dynamic update query based on provided fields
    update_fields = []
    params = []

    if bias_score is not None:
        update_fields.append("bias_score = ?")
        params.append(bias_score)

    if reasoning is not None:
        update_fields.append("reasoning = ?")
        params.append(reasoning)

    if not update_fields:
        # No fields to update
        return True

    # Always update the evaluated_at timestamp
    update_fields.append("evaluated_at = CURRENT_TIMESTAMP")

    params.append(rating_id)

    query = f"""
    UPDATE bias_ratings 
    SET {', '.join(update_fields)}
    WHERE rating_id = ?
    """

    cursor.execute(query, params)
    conn.commit()

    # Check if any rows were affected
    return cursor.rowcount > 0


def create_bias_rating(
    conn: Connection,
    article_id: int,
    bias_score: Optional[float] = None,
    reasoning: Optional[str] = None,
) -> int:
    """
    Create a new bias rating

    Args:
        conn: Database connection
        article_id: ID of the article being rated
        bias_score: Bias score
        reasoning: Reasoning behind the rating

    Returns:
        ID of the newly created bias rating
    """
    cursor = conn.cursor()

    query = """
    INSERT INTO bias_ratings (article_id, bias_score, reasoning, evaluated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """

    cursor.execute(query, (article_id, bias_score, reasoning))
    conn.commit()

    return cursor.lastrowid


def bias_rating_exists(conn: Connection, rating_id: int) -> bool:
    """
    Check if a bias rating exists

    Args:
        conn: Database connection
        rating_id: The ID of the bias rating to check

    Returns:
        True if the rating exists, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM bias_ratings WHERE rating_id = ?", (rating_id,))
    return cursor.fetchone() is not None
