import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestSummarizationEndpoint:
    """Tests for the /bias_ratings/summarize endpoint"""

    def test_summarize_missing_article_text(self):
        """Test that missing article_text returns 422"""
        response = client.post("/bias_ratings/summarize", json={})
        assert response.status_code == 422

    def test_summarize_empty_article_text(self):
        """Test that empty article_text returns 422"""
        response = client.post("/bias_ratings/summarize", json={"article_text": ""})
        assert response.status_code == 422

    def test_summarize_whitespace_only(self):
        """Test that whitespace-only article_text returns 422"""
        response = client.post(
            "/bias_ratings/summarize", json={"article_text": "   \n   "}
        )
        assert response.status_code == 422

    @patch("src.ai.summarization.genai.Client")
    def test_summarize_success(self, mock_client_class):
        """Test successful summarization - integration test with mocked Gemini API"""
        # Mock the Gemini client and response (external API)
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = "This is a concise summary of the article."
        mock_client.models.generate_content.return_value = mock_result

        # Set a fake API key
        os.environ["GEMINI_API_KEY"] = "test_key"

        try:
            response = client.post(
                "/bias_ratings/summarize",
                json={
                    "article_text": "This is a very long article about important news events that should be summarized concisely."
                },
            )

            assert response.status_code == 200
            assert response.json() == {"summary": "This is a concise summary of the article."}
        finally:
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

    @patch("src.ai.summarization.genai.Client")
    def test_summarize_gemini_api_error(self, mock_client_class):
        """Test graceful handling when Gemini API raises error"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API timeout")

        os.environ["GEMINI_API_KEY"] = "test_key"

        try:
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Sample article text for summarization."},
            )

            assert response.status_code == 502
            assert "Summary generation failed" in response.json()["detail"]
        finally:
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

    def test_summarize_missing_api_key(self):
        """Test that missing API key returns 500"""
        # Ensure no API key is set
        original_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        try:
            response = client.post(
                "/bias_ratings/summarize", json={"article_text": "Article content"}
            )

            assert response.status_code == 500
            assert "GEMINI_API_KEY not configured" in response.json()["detail"]
        finally:
            # Restore original key if it existed
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key


class TestSummarizationIntegration:
    """Integration tests for summarization with the full API"""

    def test_api_health(self):
        """Test that API is running"""
        response = client.get("/")
        assert response.status_code == 200
        assert "status" in response.json()
