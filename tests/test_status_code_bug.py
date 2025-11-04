"""
Test to verify improper handling of 4xx status codes from summarization service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from src.main import app


client = TestClient(app)


def test_400_status_code_forwarded():
    """
    BUG: When the summarization service returns a 400 (Bad Request),
    the backend doesn't handle it properly. The code only checks for:
    - status_code == 200 (success)
    - status_code >= 500 (server error -> 502)
    
    But 4xx errors (400, 422, etc.) fall through to the else clause
    which returns a generic 500 error instead of properly forwarding
    the client error.
    """
    with patch('httpx.AsyncClient') as mock_client_class:
        # Create async context manager mock
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        # Mock 400 response from summarization service
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid article text"
        mock_response.json.return_value = {"error": "Invalid article text"}
        
        # Make post return a coroutine
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article"}
        )
        
        # Correct behavior: 400 errors forwarded as 400
        assert response.status_code == 400
        assert "Invalid request to summarization service" in response.json()["detail"]


def test_422_status_code_forwarded():
    """
    BUG: Similar issue with 422 (Validation Error) from summarization service
    """
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Validation error"
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article"}
        )
        
        # Correct behavior: 422 forwarded as 422
        assert response.status_code == 422
        assert "Invalid request to summarization service" in response.json()["detail"]


def test_500_status_code_handled_correctly():
    """Verify that 500 errors ARE handled correctly (returns 502)"""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        mock_client.post = mock_post
        
        response = client.post(
            "/bias_ratings/summarize",
            json={"article_text": "Test article"}
        )
        
        # This should correctly return 502
        assert response.status_code == 502


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

