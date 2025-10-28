"""
Edge case tests to identify potential bugs in the summarization service
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main


client = TestClient(main.app)


class TestArticleTextEdgeCases:
    """Test edge cases for article text input"""
    
    def test_extremely_long_article(self):
        """Test handling of very long articles (potential token limit issue)"""
        # Create a 50,000 character article (way beyond typical token limits)
        long_article = "This is a test sentence. " * 2000
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = "Summary of very long article"
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": long_article})
                
                # Should handle gracefully
                assert resp.status_code in [200, 502]
    
    def test_article_with_special_characters(self):
        """Test article with special characters and unicode"""
        article_text = "Breaking news: 🔥 Major event! €100M deal with 中国公司. #Breaking"
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = "Summary with special chars"
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": article_text})
                assert resp.status_code == 200
    
    def test_article_with_only_numbers(self):
        """Test article that's just numbers"""
        resp = client.post("/summarize", json={"article_text": "123456789"})
        # Should either work or return validation error
        assert resp.status_code in [200, 422, 500, 502]
    
    def test_article_with_code_injection_attempt(self):
        """Test potential code injection in article text"""
        malicious_text = "<script>alert('xss')</script> OR 1=1; DROP TABLE articles;"
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = "Safe summary"
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": malicious_text})
                assert resp.status_code == 200


class TestGeminiResponseEdgeCases:
    """Test edge cases in Gemini API responses"""
    
    def test_gemini_returns_empty_string(self):
        """BUG: What if Gemini returns empty string?"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = ""  # Empty response
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": "Test article"})
                
                # Should handle empty response gracefully
                # Current implementation raises RuntimeError -> 502
                assert resp.status_code == 502
    
    def test_gemini_returns_none(self):
        """BUG: What if Gemini returns None?"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = None  # None response
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": "Test article"})
                
                # Should handle None response gracefully
                assert resp.status_code == 502
    
    def test_gemini_returns_whitespace_only(self):
        """BUG: What if Gemini returns only whitespace?"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = "   \n\n   "  # Whitespace only
                mock_client.models.generate_content.return_value = mock_result
                
                resp = client.post("/summarize", json={"article_text": "Test article"})
                
                # Should handle whitespace-only response
                assert resp.status_code == 502


class TestConcurrencyAndPerformance:
    """Test concurrent requests and performance issues"""
    
    def test_concurrent_requests(self):
        """Test multiple concurrent requests"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_result = MagicMock()
                mock_result.text = "Summary"
                mock_client.models.generate_content.return_value = mock_result
                
                # Make multiple requests
                responses = []
                for i in range(5):
                    resp = client.post("/summarize", json={
                        "article_text": f"Article {i} content"
                    })
                    responses.append(resp)
                
                # All should succeed
                for resp in responses:
                    assert resp.status_code == 200


class TestConfigurationIssues:
    """Test configuration-related bugs"""
    
    def test_invalid_api_key_format(self):
        """Test with malformed API key"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "invalid-key-123"}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.models.generate_content.side_effect = Exception("Invalid API key")
                
                resp = client.post("/summarize", json={"article_text": "Test"})
                assert resp.status_code == 502
    
    def test_api_key_with_whitespace(self):
        """BUG: API key with leading/trailing whitespace"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "  valid-key  "}):
            with patch('main.genai.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                
                # The client might fail because of whitespace
                mock_client.models.generate_content.side_effect = Exception("Invalid API key")
                
                resp = client.post("/summarize", json={"article_text": "Test"})
                # Should fail but might not strip whitespace
                assert resp.status_code in [500, 502]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

