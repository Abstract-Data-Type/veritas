"""
Integration tests to identify bugs in the main backend's summarization integration
"""

from unittest.mock import patch

import pytest


class TestPipelineIntegrationBugs:
    """Test bugs in the pipeline integration"""

    @pytest.mark.asyncio
    async def test_pipeline_with_missing_service(self):
        """Test pipeline when summarization service is down"""

        from veritas_news.worker.pipeline import ArticlePipeline

        pipeline = ArticlePipeline()

        # Try to get summary when service is down
        summary = await pipeline._get_article_summary("Test article text")

        # Should return None gracefully
        assert summary is None

    @pytest.mark.asyncio
    async def test_pipeline_with_very_short_text(self):
        """BUG: Pipeline skips summarization for short text"""
        from veritas_news.worker.pipeline import ArticlePipeline

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
        from veritas_news.worker.pipeline import ArticlePipeline

        pipeline = ArticlePipeline()

        # Exactly 50 characters
        text_50 = "a" * 50

        # Mock the AI library function where it's imported in the pipeline module
        with patch("veritas_news.worker.pipeline.summarize_with_gemini") as mock_summarize:
            mock_summarize.return_value = "Summary of fifty character text"

            summary = await pipeline._get_article_summary(text_50)

            # Should process since it's >= 50 chars (not < 50)
            # The pipeline checks: if len(article_text.strip()) < 50: return None
            # So 50 chars should be processed
            assert summary is not None
            assert summary == "Summary of fifty character text"
            mock_summarize.assert_called_once_with(text_50)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
