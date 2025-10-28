"""
Test to identify the empty summary bug
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from src.main import app


client = TestClient(app)


def test_empty_summary_returned_as_success():
    """
    CRITICAL BUG: Backend returns 200 OK with empty summary when service
    returns malformed JSON without 'summary' field.
    
    Location: src/api/routes_bias_ratings.py line 198
    Code: return {"summary": data.get("summary", "")}
    
    Problem: If the summarization service returns 200 OK but the JSON
    doesn't contain a 'summary' field, the backend returns an empty string
    as a "successful" summary instead of treating it as an error.
    
    This is a silent failure that could confuse users and downstream systems.
    """
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        # Mock response with 200 but missing 'summary' field
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"wrong_field": "data", "error": "something"}
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article content here"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # BUG: Returns 200 with empty summary instead of error
        assert response.status_code == 200
        data = response.json()
        assert data.get("summary") == ""  # Empty string!
        
        print("\n🐛 BUG CONFIRMED:")
        print("Backend returns 200 OK with empty summary when service")
        print("returns malformed JSON without 'summary' field.")
        print("This is a SILENT FAILURE - users get empty summary as 'success'")


def test_empty_summary_string_returned_as_success():
    """
    CRITICAL BUG: Backend returns 200 OK even when summary is explicitly empty string
    """
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        # Service returns 200 with empty summary
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"summary": ""}
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article"}
        )
        
        # BUG: Returns 200 with empty summary
        assert response.status_code == 200
        assert response.json()["summary"] == ""
        
        print("\n🐛 BUG CONFIRMED:")
        print("Backend accepts empty summary string as valid response")
        print("Should validate that summary is non-empty before returning success")


def test_whitespace_only_summary_returned_as_success():
    """
    CRITICAL BUG: Backend returns whitespace-only summary as success
    """
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        # Service returns 200 with whitespace-only summary
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"summary": "   \n\n   "}
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article"}
        )
        
        # BUG: Returns 200 with whitespace summary
        assert response.status_code == 200
        assert response.json()["summary"].strip() == ""
        
        print("\n🐛 BUG CONFIRMED:")
        print("Backend accepts whitespace-only summary as valid")
        print("Should validate that summary contains actual content")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

