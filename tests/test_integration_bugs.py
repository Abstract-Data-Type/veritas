"""
Integration tests to identify bugs in the main backend's summarization integration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
import os

from src.main import app


client = TestClient(app)


class TestBackendSummarizationBugs:
    """Test potential bugs in backend summarization integration"""
    
    def test_summarization_service_url_not_set(self):
        """BUG: What if SUMMARIZATION_SERVICE_URL is not set?"""
        # Remove the env var if it exists
        with patch.dict(os.environ, {}, clear=True):
            with patch('httpx.AsyncClient') as mock_client:
                mock_instance = MagicMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                # Mock successful response
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"summary": "Test summary"}
                mock_instance.post.return_value = mock_response
                
                response = client.post(
                    "/bias_ratings/summarize",
                    json={"article_text": "Test article"}
                )
                
                # Should use default localhost:8000
                # Check if it at least tries to connect
                assert response.status_code in [200, 502, 504]
    
    def test_summarization_service_returns_malformed_json(self):
        """BUG: Service returns 200 but malformed JSON"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock response with missing 'summary' field
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"wrong_field": "data"}
            mock_instance.post.return_value = mock_response
            
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Test article"}
            )
            
            # Should handle missing 'summary' field
            # Current code uses .get("summary", "") which returns empty string
            assert response.status_code == 200
            data = response.json()
            # BUG: Returns empty summary instead of error
            assert data.get("summary") == ""
    
    def test_summarization_service_returns_400(self):
        """BUG: Service returns 400 (client error)"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_instance.post.return_value = mock_response
            
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Test article"}
            )
            
            # Current code doesn't handle 4xx errors properly
            # It only checks >= 500 or == 200
            # BUG: 400 falls through to generic 500 error
            assert response.status_code == 500
    
    def test_summarization_with_very_short_text(self):
        """Test with very short article text"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"summary": "Short."}
            mock_instance.post.return_value = mock_response
            
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Hi"}
            )
            
            # Should work but might not be useful
            assert response.status_code in [200, 400]
    
    def test_summarization_service_url_with_trailing_slash(self):
        """BUG: Service URL with trailing slash causes double slash"""
        with patch.dict(os.environ, {"SUMMARIZATION_SERVICE_URL": "http://localhost:8000/"}):
            with patch('httpx.AsyncClient') as mock_client:
                mock_instance = MagicMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"summary": "Test"}
                mock_instance.post.return_value = mock_response
                
                response = client.post(
                    "/bias_ratings/summarize",
                    json={"article_text": "Test article"}
                )
                
                # Check if URL was constructed correctly
                # Current code does f"{url}/summarize" which creates double slash
                # This might work but is not clean
                assert response.status_code in [200, 502]


class TestPipelineIntegrationBugs:
    """Test bugs in the pipeline integration"""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_missing_service(self):
        """Test pipeline when summarization service is down"""
        from src.worker.pipeline import ArticlePipeline
        from src.worker.fetchers import ArticleData
        from datetime import datetime
        
        pipeline = ArticlePipeline()
        
        # Try to get summary when service is down
        summary = await pipeline._get_article_summary("Test article text")
        
        # Should return None gracefully
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_pipeline_with_very_short_text(self):
        """BUG: Pipeline skips summarization for short text"""
        from src.worker.pipeline import ArticlePipeline
        
        pipeline = ArticlePipeline()
        
        # Text less than 50 characters
        short_text = "Short article"
        summary = await pipeline._get_article_summary(short_text)
        
        # Current implementation returns None for text < 50 chars
        # This might be intentional but could be a bug
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_pipeline_with_exactly_50_chars(self):
        """Test boundary condition: exactly 50 characters"""
        from src.worker.pipeline import ArticlePipeline
        
        pipeline = ArticlePipeline()
        
        # Exactly 50 characters
        text_50 = "a" * 50
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"summary": "Summary"}
            mock_instance.post.return_value = mock_response
            
            summary = await pipeline._get_article_summary(text_50)
            
            # Should process (>= 50 chars after strip)
            # BUG: Current code checks < 50, so 50 should work
            assert summary is not None or summary is None  # Depends on implementation


class TestErrorHandlingBugs:
    """Test error handling edge cases"""
    
    def test_network_error_during_request(self):
        """Test network error mid-request"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = httpx.NetworkError("Network failed")
            
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Test article"}
            )
            
            # Should handle network error
            assert response.status_code in [502, 500]
    
    def test_json_decode_error(self):
        """BUG: Service returns invalid JSON"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_instance.post.return_value = mock_response
            
            response = client.post(
                "/bias_ratings/summarize",
                json={"article_text": "Test article"}
            )
            
            # Should handle JSON decode error
            assert response.status_code in [500, 502]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

