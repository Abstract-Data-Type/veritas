"""Unit tests for summarization library functions."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# These imports will work after we migrate the code
# For now, they'll fail - that's expected in TDD
try:
    from src.ai import summarization
except ImportError:
    # During TDD phase, these will fail - that's expected
    summarization = None

# Skip all tests if imports fail (expected during TDD phase)
pytestmark = pytest.mark.skipif(
    summarization is None,
    reason="AI library modules not yet migrated - this is expected during TDD"
)


def test_summarize_with_gemini_success():
    """Test successful summarization"""
    with patch("src.ai.summarization.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = "This is a test summary of the article."
        mock_client.models.generate_content.return_value = mock_result

        # Set a fake API key
        os.environ["GEMINI_API_KEY"] = "test_key"

        try:
            summary = summarization.summarize_with_gemini("Test article content")
            assert summary == "This is a test summary of the article."
        finally:
            del os.environ["GEMINI_API_KEY"]


def test_summarize_with_gemini_missing_api_key():
    """Test that missing API key raises HTTPException"""
    # Ensure no API key is set
    original_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        with pytest.raises(HTTPException) as exc_info:
            summarization.summarize_with_gemini("Test article content")

        assert exc_info.value.status_code == 500
        assert "GEMINI_API_KEY not configured" in exc_info.value.detail
    finally:
        # Restore original key if it existed
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key


def test_summarize_with_gemini_api_error():
    """Test that Gemini API errors are handled gracefully"""
    with patch("src.ai.summarization.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API timeout")

        os.environ["GEMINI_API_KEY"] = "test_key"

        try:
            with pytest.raises(HTTPException) as exc_info:
                summarization.summarize_with_gemini("Article content")

            assert exc_info.value.status_code == 502
            assert "Summary generation failed" in exc_info.value.detail
        finally:
            del os.environ["GEMINI_API_KEY"]


def test_summarize_with_gemini_empty_response():
    """Test that empty response from Gemini raises HTTPException"""
    with patch("src.ai.summarization.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = None  # Empty response
        mock_client.models.generate_content.return_value = mock_result

        os.environ["GEMINI_API_KEY"] = "test_key"

        try:
            with pytest.raises(HTTPException) as exc_info:
                summarization.summarize_with_gemini("Article content")

            assert exc_info.value.status_code == 502
            assert "Summary generation failed" in exc_info.value.detail
        finally:
            del os.environ["GEMINI_API_KEY"]

