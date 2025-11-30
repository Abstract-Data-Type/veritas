"""Bias analysis using LLM calls."""

import asyncio
import os
import re

from fastapi import HTTPException
from google import genai
from google.genai import types

from .config import get_prompts_config
from .scoring import score_bias


def parse_llm_score(response_text: str) -> float:
    """
    Parse LLM response and extract numeric score.

    Handles edge cases:
    - Text responses like "five" → extract number
    - Float values like 7.2 → clamp to 1-7 range
    - Invalid responses → raise ValueError

    Args:
        response_text: Raw text response from LLM

    Returns:
        Parsed score as float (1-7 inclusive)

    Raises:
        ValueError: If response cannot be parsed or is invalid
    """
    if not response_text or not response_text.strip():
        raise ValueError("Empty response from LLM")

    text = response_text.strip()

    # Try to find a number in the response (handles "The score is 5" or "5.0")
    # Look for decimal numbers first, then integers
    number_patterns = [
        r"\b(\d+\.\d+)\b",  # Decimal numbers like 5.2
        r"\b(\d+)\b",  # Integers like 5
    ]

    for pattern in number_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                score = float(match.group(1))
                # Clamp to valid range [1, 7]
                score = max(1.0, min(7.0, score))
                return score
            except (ValueError, AttributeError):
                continue

    # Try to parse written numbers (one, two, three, etc.)
    written_numbers = {
        "one": 1.0,
        "two": 2.0,
        "three": 3.0,
        "four": 4.0,
        "five": 5.0,
        "six": 6.0,
        "seven": 7.0,
    }
    text_lower = text.lower()
    for word, num in written_numbers.items():
        if word in text_lower:
            return num

    # If we can't parse it, raise an error
    raise ValueError(f"Could not extract valid score from response: {text}")


def _call_gemini_sync(
    article_text: str, prompt: str, model: str, temperature: float
) -> str:
    """
    Synchronous wrapper for Gemini API call.
    This function is called from within asyncio.to_thread().

    Args:
        article_text: The article text to analyze
        prompt: The dimension-specific prompt
        model: Gemini model name
        temperature: Temperature setting for generation

    Returns:
        Raw text response from Gemini

    Raises:
        Exception: If API call fails
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    full_prompt = f"""{prompt}

Article text:
{article_text}"""

    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=full_prompt)],
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=2000,  # High limit to ensure all prompts work regardless of length or complexity
    )

    result = client.models.generate_content(
        model=model, contents=contents, config=generate_content_config
    )

    # Extract text from result - handle both result.text and candidate.content.parts
    response_text = result.text
    if not response_text and result.candidates:
        # Fallback: extract text from candidate parts if result.text is None
        candidate = result.candidates[0]
        if candidate.content and candidate.content.parts:
            text_parts = [
                part.text
                for part in candidate.content.parts
                if hasattr(part, "text") and part.text
            ]
            if text_parts:
                response_text = " ".join(text_parts)

    response_text = (response_text or "").strip()
    if not response_text:
        raise RuntimeError("Empty response from Gemini API")

    return response_text


async def call_llm_for_dimension(
    article_text: str,
    dimension_config: dict[str, str],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.1,
) -> float:
    """
    Async wrapper for Gemini API call that processes a single bias dimension.

    Args:
        article_text: The full text of the article to analyze
        dimension_config: Dictionary with 'name' and 'prompt' keys
        model: Gemini model name (default: gemini-2.5-flash)
        temperature: Temperature for generation (default: 0.1)

    Returns:
        Parsed score as float (1-7)

    Raises:
        Exception: If API call fails or response cannot be parsed
    """
    prompt = dimension_config["prompt"]

    # Run synchronous Gemini call in thread pool
    response_text = await asyncio.to_thread(
        _call_gemini_sync, article_text, prompt, model, temperature
    )

    # Parse and validate the response
    score = parse_llm_score(response_text)
    return score


async def rate_bias_parallel(
    article_text: str,
    dimension_configs: list[dict[str, str]],
    model: str = "gemini-2.5-flash",
) -> dict[str, float]:
    """
    Orchestrate parallel LLM calls for all bias dimensions.

    Creates N async tasks (one per dimension) and executes them concurrently.
    If any call fails, the entire operation fails (atomic requirement).

    Args:
        article_text: The full text of the article to analyze
        dimension_configs: List of dimension configurations
        model: Gemini model name

    Returns:
        Dictionary mapping dimension names to scores

    Raises:
        HTTPException: 502 if any LLM call fails
    """
    # Create async tasks for all dimensions
    tasks = [
        call_llm_for_dimension(article_text, dim_config, model)
        for dim_config in dimension_configs
    ]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check for failures - if any task failed, fail the entire request (atomic)
    scores = {}
    errors = []

    for i, result in enumerate(results):
        dim_name = dimension_configs[i]["name"]

        if isinstance(result, Exception):
            errors.append(f"Dimension '{dim_name}': {str(result)}")
        else:
            scores[dim_name] = result

    # If any call failed, raise 502 (atomic requirement)
    if errors:
        error_msg = "; ".join(errors)
        raise HTTPException(status_code=502, detail=f"Bias rating failed: {error_msg}")

    return scores


async def rate_bias(article_text: str) -> dict[str, any]:
    """
    Main function to rate bias for an article (converted from FastAPI endpoint).

    Makes N parallel LLM calls (one per bias dimension) and returns compiled scores.
    The function is atomic: if any dimension analysis fails, the entire request fails.

    Args:
        article_text: The full text of the article to analyze (required, non-empty)

    Returns:
        Dictionary with:
        - scores: Dictionary mapping dimension names to scores (1.0-7.0)
        - ai_model: The AI model used for analysis

    Raises:
        HTTPException: 500 if config/API key missing, 502 if LLM calls fail
    """
    model = "gemini-2.5-flash"

    # Get prompts configuration (cached at module level)
    try:
        dimension_configs = get_prompts_config()
    except HTTPException:
        # Re-raise config errors as-is (already 500 status)
        raise

    # Validate API key is configured
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    # Execute parallel LLM calls for all dimensions
    try:
        raw_scores = await rate_bias_parallel(article_text, dimension_configs, model)
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 502 from rate_bias_parallel)
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(status_code=502, detail=f"Bias rating failed: {str(e)}")

    # Apply scoring function (currently pass-through)
    final_scores = score_bias(raw_scores)

    return {"scores": final_scores, "ai_model": model}

