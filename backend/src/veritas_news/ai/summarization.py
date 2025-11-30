"""Article summarization using Gemini API."""

import os

from fastapi import HTTPException
from google import genai
from google.genai import types

from .config import get_summarization_prompt_template


def summarize_with_gemini(article_text: str) -> str:
    """
    Call Gemini API to generate a concise summary of the article text.

    Args:
        article_text: The full text of the article to summarize

    Returns:
        A concise summary string

    Raises:
        HTTPException: 500 if API key missing, 502 if upstream fails
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"

        # Load prompt template from config and format with article text
        prompt_template = get_summarization_prompt_template()
        prompt = prompt_template.format(article_text=article_text)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=0.3,  # Lower temperature for more focused summaries
            max_output_tokens=150,  # Limit summary length
        )

        # Use synchronous call for web handler
        result = client.models.generate_content(
            model=model, contents=contents, config=generate_content_config
        )

        summary_text = (result.text or "").strip()

        if not summary_text:
            raise RuntimeError("Empty summary returned from model")

        return summary_text

    except HTTPException:
        # Re-raise our own HTTP exceptions
        raise
    except Exception:
        # Map any upstream/model errors to 502 Bad Gateway
        raise HTTPException(status_code=502, detail="Summary generation failed")

