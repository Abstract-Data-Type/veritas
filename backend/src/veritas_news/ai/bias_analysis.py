"""Bias analysis using LLM calls."""

import asyncio
import os
import re
from typing import Any

from fastapi import HTTPException
from google import genai
from google.genai import types

from .config import get_prompts_config, get_secm_config
from .scoring import score_bias, score_secm


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
    max_retries: int = 5,
    retry_delay: float = 1.0,
) -> float:
    """
    Async wrapper for Gemini API call that processes a single bias dimension.

    Args:
        article_text: The full text of the article to analyze
        dimension_config: Dictionary with 'name' and 'prompt' keys
        model: Gemini model name (default: gemini-2.5-flash)
        temperature: Temperature for generation (default: 0.1)
        max_retries: Maximum number of retry attempts (default: 5)
        retry_delay: Delay between retries in seconds (default: 1.0)

    Returns:
        Parsed score as float (1-7)

    Raises:
        Exception: If API call fails after all retries
    """
    prompt = dimension_config["prompt"]
    dim_name = dimension_config.get("name", "unknown")
    last_error = None

    for attempt in range(max_retries):
        try:
            # Run synchronous Gemini call in thread pool
            response_text = await asyncio.to_thread(
                _call_gemini_sync, article_text, prompt, model, temperature
            )

            # Parse and validate the response
            score = parse_llm_score(response_text)
            return score

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import logging
                import os
                
                # Check if this is a 503 overload error
                is_503_overload = (
                    "503" in str(e) and 
                    ("overloaded" in str(e).lower() or "unavailable" in str(e).lower())
                )
                
                if is_503_overload:
                    # Use longer delay for 503 overload errors
                    delay = float(os.getenv("GEMINI_503_RETRY_DELAY", "5"))
                    logging.getLogger(__name__).warning(
                        f"Dimension '{dim_name}' attempt {attempt + 1}/{max_retries} failed: 503 overload. Waiting {delay}s before retry..."
                    )
                    await asyncio.sleep(delay)
                else:
                    # Standard exponential backoff for other errors
                    logging.getLogger(__name__).warning(
                        f"Dimension '{dim_name}' attempt {attempt + 1}/{max_retries} failed: {e}. Retrying..."
                    )
                    await asyncio.sleep(retry_delay * (attempt + 1))

    raise last_error or RuntimeError(f"Dimension '{dim_name}' failed with no error details")


async def rate_bias_parallel(
    article_text: str,
    dimension_configs: list[dict[str, str]],
    model: str = "gemini-2.5-flash",
) -> dict[str, float]:
    """
    Orchestrate parallel LLM calls for all bias dimensions.

    Creates N async tasks (one per dimension) and executes them concurrently.
    Returns partial results if some dimensions fail (resilient mode).

    Args:
        article_text: The full text of the article to analyze
        dimension_configs: List of dimension configurations
        model: Gemini model name

    Returns:
        Dictionary mapping dimension names to scores (may be partial)

    Raises:
        HTTPException: 502 only if ALL dimensions fail
    """
    # Create async tasks for all dimensions
    tasks = [
        call_llm_for_dimension(article_text, dim_config, model)
        for dim_config in dimension_configs
    ]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scores = {}
    errors = []

    for i, result in enumerate(results):
        dim_name = dimension_configs[i]["name"]

        if isinstance(result, Exception):
            errors.append(f"Dimension '{dim_name}': {str(result)}")
        else:
            scores[dim_name] = result

    # Log errors but continue with partial results
    if errors:
        import logging
        logging.getLogger(__name__).warning(f"Some bias dimensions failed: {'; '.join(errors)}")

    # Only fail if ALL dimensions failed
    if not scores:
        raise HTTPException(status_code=502, detail=f"Bias rating failed: {'; '.join(errors)}")

    return scores


async def rate_bias(article_text: str) -> dict[str, Any]:
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


def parse_secm_response(response_text: str) -> tuple[int, str]:
    """
    Parse SECM LLM response with XML tags.
    
    Extracts reasoning from <reasoning> tags and binary answer from <answer> tags.
    Falls back to fuzzy matching if XML tags are missing.
    
    Args:
        response_text: Raw text response from LLM
    
    Returns:
        Tuple of (binary_answer: 0 or 1, reasoning: str)
    
    Raises:
        ValueError: If response cannot be parsed
    """
    if not response_text or not response_text.strip():
        raise ValueError("Empty response from LLM")
    
    text = response_text.strip()
    
    # Try to extract reasoning from XML tags
    reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", text, re.DOTALL | re.IGNORECASE)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
    
    # Try to extract answer from XML tags
    answer_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL | re.IGNORECASE)
    if answer_match:
        answer_text = answer_match.group(1).strip()
        # Extract 0 or 1 from answer tag
        if "1" in answer_text or "one" in answer_text.lower():
            binary_answer = 1
        elif "0" in answer_text or "zero" in answer_text.lower() or "absent" in answer_text.lower():
            binary_answer = 0
        else:
            raise ValueError(f"Could not parse binary answer from <answer> tag: {answer_text}")
    else:
        # Fallback: search for 0 or 1 in the text
        if re.search(r"\b1\b", text) or "present" in text.lower() or "yes" in text.lower():
            binary_answer = 1
        elif re.search(r"\b0\b", text) or "absent" in text.lower() or "no" in text.lower():
            binary_answer = 0
        else:
            raise ValueError(f"Could not extract binary answer from response: {text}")
    
    # If no reasoning found, use empty string
    if not reasoning:
        reasoning = ""
    
    return binary_answer, reasoning


async def call_llm_for_secm_variable(
    article_text: str,
    variable_config: dict[str, str],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.1,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> tuple[int, str]:
    """
    Call LLM for a single SECM variable with retry logic.
    
    Args:
        article_text: The full text of the article to analyze
        variable_config: Dictionary with 'name' and 'prompt' keys
        model: Gemini model name (default: gemini-2.5-flash)
        temperature: Temperature for generation (default: 0.1)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)
    
    Returns:
        Tuple of (binary_answer: 0 or 1, reasoning: str)
    
    Raises:
        Exception: If API call fails after all retries
    """
    prompt = variable_config["prompt"]
    var_name = variable_config.get("name", "unknown")
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Run synchronous Gemini call in thread pool
            response_text = await asyncio.to_thread(
                _call_gemini_sync, article_text, prompt, model, temperature
            )
            
            # Parse and validate the response
            binary_answer, reasoning = parse_secm_response(response_text)
            return binary_answer, reasoning
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Log retry attempt and wait before next try
                import logging
                logging.getLogger(__name__).warning(
                    f"SECM variable '{var_name}' attempt {attempt + 1}/{max_retries} failed: {e}. Retrying..."
                )
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                # Final attempt failed
                import logging
                logging.getLogger(__name__).error(
                    f"SECM variable '{var_name}' failed after {max_retries} attempts: {e}"
                )
    
    # All retries exhausted
    raise last_error or RuntimeError(f"SECM variable '{var_name}' failed with no error details")


async def rate_secm_parallel(
    article_text: str,
    variable_configs: list[dict[str, str]],
    model: str = "gemini-2.5-flash",
) -> dict[str, tuple[int, str]]:
    """
    Orchestrate parallel LLM calls for all SECM variables.
    
    Creates N async tasks (one per variable) and executes them concurrently.
    Returns partial results if some variables fail (resilient mode).
    
    Args:
        article_text: The full text of the article to analyze
        variable_configs: List of variable configurations
        model: Gemini model name
    
    Returns:
        Dictionary mapping variable names to (answer, reasoning) tuples (may be partial)
    
    Raises:
        HTTPException: 502 only if ALL variables fail
    """
    # Create async tasks for all variables
    tasks = [
        call_llm_for_secm_variable(article_text, var_config, model)
        for var_config in variable_configs
    ]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    variable_results: dict[str, tuple[int, str]] = {}
    errors = []
    
    for i, result in enumerate(results):
        var_name = variable_configs[i]["name"]
        
        if isinstance(result, Exception):
            errors.append(f"Variable '{var_name}': {str(result)}")
        else:
            variable_results[var_name] = result
    
    # Log errors but continue with partial results
    if errors:
        import logging
        logging.getLogger(__name__).warning(f"Some SECM variables failed: {'; '.join(errors)}")
    
    # Only fail if ALL variables failed
    if not variable_results:
        raise HTTPException(status_code=502, detail=f"SECM rating failed: {'; '.join(errors)}")
    
    return variable_results


async def rate_secm(article_text: str) -> dict[str, Any]:
    """
    Main SECM analysis function.
    
    Makes 22 parallel LLM calls (one per SECM variable) and computes final scores.
    The function is atomic: if any variable analysis fails, the entire request fails.
    
    Args:
        article_text: The full text of the article to analyze (required, non-empty)
    
    Returns:
        Dictionary with:
        - ideological_score: float (-1.0 to +1.0)
        - epistemic_score: float (-1.0 to +1.0)
        - variables: Dictionary mapping variable names to binary values (0/1)
        - reasoning: Dictionary mapping variable names to reasoning strings
        - ai_model: The AI model used for analysis
    
    Raises:
        HTTPException: 500 if config/API key missing, 502 if LLM calls fail
    """
    model = "gemini-2.5-flash"
    
    # Get SECM configuration (cached at module level)
    try:
        secm_config = get_secm_config()
    except HTTPException:
        # Re-raise config errors as-is (already 500 status)
        raise
    
    # Validate API key is configured
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    
    # Execute parallel LLM calls for all variables
    try:
        variable_results = await rate_secm_parallel(
            article_text, secm_config["variables"], model
        )
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 502 from rate_secm_parallel)
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(status_code=502, detail=f"SECM rating failed: {str(e)}")
    
    # Extract variables and reasoning dictionaries
    variables = {name: result[0] for name, result in variable_results.items()}
    reasoning = {name: result[1] for name, result in variable_results.items()}
    
    # Compute final scores using SECM scoring algorithm with Bayesian smoothing
    k = secm_config["k"]
    final_scores = score_secm(variables, k)
    
    return {
        "ideological_score": final_scores["ideological_score"],
        "epistemic_score": final_scores["epistemic_score"],
        "variables": variables,
        "reasoning": reasoning,
        "ai_model": model,
    }

