import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main


client = TestClient(main.app)


def test_root_endpoint():
    """Test health check endpoint"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "summarization"}


def test_missing_article_text_returns_422():
    """Test that missing article_text returns validation error"""
    resp = client.post("/summarize", json={})
    assert resp.status_code == 422  # Pydantic validation error


def test_empty_article_text_returns_422():
    """Test that empty article_text returns validation error"""
    resp = client.post("/summarize", json={"article_text": ""})
    assert resp.status_code == 422


def test_whitespace_only_article_text_returns_422():
    """Test that whitespace-only article_text returns validation error"""
    resp = client.post("/summarize", json={"article_text": "   "})
    assert resp.status_code == 422


@patch('main.summarize_with_gemini')
def test_llm_failure_returns_502(mock_summarize):
    """Test that LLM failures are mapped to 502 Bad Gateway"""
    from fastapi import HTTPException
    mock_summarize.side_effect = HTTPException(status_code=502, detail="Summary generation failed")
    
    resp = client.post("/summarize", json={"article_text": "Test article content"})
    assert resp.status_code == 502
    assert "Summary generation failed" in resp.json()["detail"]


@patch('main.summarize_with_gemini')
def test_success_returns_summary(mock_summarize):
    """Test successful summarization"""
    mock_summarize.return_value = "This is a test summary of the article."
    
    resp = client.post("/summarize", json={
        "article_text": "This is a long article about important news events."
    })
    
    assert resp.status_code == 200
    assert resp.json() == {"summary": "This is a test summary of the article."}


@patch('main.genai.Client')
def test_gemini_integration_success(mock_client_class):
    """Test actual Gemini client integration (mocked)"""
    # Mock the Gemini client and response
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_result = MagicMock()
    mock_result.text = "Generated summary from Gemini"
    mock_client.models.generate_content.return_value = mock_result
    
    # Set a fake API key
    os.environ["GEMINI_API_KEY"] = "test_key"
    
    resp = client.post("/summarize", json={
        "article_text": "Article content here"
    })
    
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Generated summary from Gemini"
    
    # Clean up
    del os.environ["GEMINI_API_KEY"]


@patch('main.genai.Client')
def test_gemini_api_error_returns_502(mock_client_class):
    """Test that Gemini API errors are handled gracefully"""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API timeout")
    
    os.environ["GEMINI_API_KEY"] = "test_key"
    
    resp = client.post("/summarize", json={
        "article_text": "Article content"
    })
    
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Summary generation failed"
    
    del os.environ["GEMINI_API_KEY"]


def test_missing_api_key_returns_500():
    """Test that missing API key returns 500"""
    # Ensure no API key is set
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    resp = client.post("/summarize", json={
        "article_text": "Article content"
    })
    
    assert resp.status_code == 500
    assert "GEMINI_API_KEY not configured" in resp.json()["detail"]

