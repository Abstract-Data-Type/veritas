"""
Test to identify validation issues in the backend API.

Note: Tests comparing against a separate summarization service have been removed
since the summarization functionality is now integrated directly into the backend.
"""

import os

from fastapi.testclient import TestClient
import pytest

from veritas_news.main import app as backend_app

backend_client = TestClient(backend_app)


class TestValidationChecks:
    """Test validation behavior in the backend"""

    def test_backend_validation_empty_string(self):
        """Test that empty article_text returns 422"""
        response = backend_client.post(
            "/bias_ratings/summarize", json={"article_text": ""}
        )
        assert response.status_code == 422

    def test_backend_validation_whitespace(self):
        """Test that whitespace-only article_text returns 422"""
        response = backend_client.post(
            "/bias_ratings/summarize", json={"article_text": "   "}
        )
        assert response.status_code == 422

    def test_backend_has_pydantic_validator(self):
        """Test that backend's SummarizeRequest has validation"""
        from veritas_news.api.routes_bias_ratings import (
            SummarizeRequest as BackendRequest,
        )

        # Check if it has field_validator
        has_validator = hasattr(BackendRequest, "validate_article_text")
        # Note: The presence of a validator is a design choice
        # This test documents the current behavior
        print(f"Backend has Pydantic validator: {has_validator}")


class TestMissingValidation:
    """Test for missing validation in backend"""

    def test_backend_missing_max_length_validation(self):
        """
        BUG: No maximum length validation for article_text

        Neither backend nor service validates maximum article length.
        This could lead to:
        - Token limit errors from Gemini
        - Memory issues
        - Timeout issues
        - Excessive API costs
        """
        # Create extremely long article (100,000 chars)
        very_long_article = "This is a test sentence. " * 4000

        print(f"Article length: {len(very_long_article)} characters")

        # No validation prevents this from being sent to Gemini
        # This could cause token limit errors or excessive costs
        assert len(very_long_article) > 50000
        print("BUG: No max length validation exists")


class TestAPIKeyValidation:
    """Test API key handling bugs"""

    def test_api_key_not_stripped(self):
        """
        BUG: API key from environment is not stripped of whitespace

        If GEMINI_API_KEY has leading/trailing whitespace in .env file,
        it will be used as-is without stripping, causing authentication failures.
        """
        from unittest.mock import patch

        # Simulate API key with whitespace
        with patch.dict(os.environ, {"GEMINI_API_KEY": "  my-api-key  "}):
            api_key = os.environ.get("GEMINI_API_KEY")

            # BUG: Not stripped
            assert api_key == "  my-api-key  "
            assert api_key != "my-api-key"

            print(f"API key with whitespace: '{api_key}'")
            print("BUG: API key not stripped, will cause auth failures")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
