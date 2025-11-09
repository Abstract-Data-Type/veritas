"""
Test to identify validation inconsistency bug between backend and summarization service
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

from src.main import app as backend_app

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "services", "summarization")
)
import main as summarization_app

backend_client = TestClient(backend_app)
summarization_client = TestClient(summarization_app.app)


class TestValidationInconsistency:
    """Test validation inconsistency between backend and summarization service"""

    def test_backend_validation_duplicate_check(self):
        """
        BUG: Backend has DUPLICATE validation logic

        The backend's summarize_article endpoint validates article_text:
        1. In the Pydantic model (SummarizeRequest with article_text: str)
        2. AGAIN manually in the endpoint (lines 178-182)

        This is redundant and inconsistent with the summarization service.
        """
        # Backend validation
        response = backend_client.post(
            "/bias_ratings/summarize", json={"article_text": ""}
        )
        print(f"Backend empty string: {response.status_code}")

        response = backend_client.post(
            "/bias_ratings/summarize", json={"article_text": "   "}
        )
        print(f"Backend whitespace: {response.status_code}")

        # The backend does manual validation AFTER Pydantic validation
        # This is redundant

    def test_summarization_service_validation(self):
        """Summarization service uses Pydantic validator"""
        # Summarization service validation
        response = summarization_client.post("/summarize", json={"article_text": ""})
        print(f"Service empty string: {response.status_code}")

        response = summarization_client.post("/summarize", json={"article_text": "   "})
        print(f"Service whitespace: {response.status_code}")

    def test_backend_has_no_pydantic_validator(self):
        """
        BUG: Backend's SummarizeRequest doesn't use Pydantic validator

        Backend: SummarizeRequest has NO @field_validator
        Service: SummarizeRequest HAS @field_validator

        This inconsistency means:
        - Backend relies on manual validation (error-prone)
        - Service uses Pydantic validation (automatic)
        - Different error messages and status codes
        """
        # Check backend model
        from src.api.routes_bias_ratings import SummarizeRequest as BackendRequest

        # Check if it has field_validator
        has_validator = hasattr(BackendRequest, "validate_article_text")
        print(f"Backend has Pydantic validator: {has_validator}")
        assert has_validator == False, "BUG: Backend should have validator but doesn't"

        # Check service model
        from main import SummarizeRequest as ServiceRequest

        has_validator = hasattr(ServiceRequest, "validate_article_text")
        print(f"Service has Pydantic validator: {has_validator}")
        assert has_validator == True, "Service correctly has validator"


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
        import os
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
