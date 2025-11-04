import os
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from google import genai
from google.genai import types
from dotenv import load_dotenv

from config import get_prompts_config
from bias_analysis import rate_bias_parallel
from scoring import score_bias


# Load .env from project root (parent directory)
# This ensures we use the same .env file as the main backend
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


class SummarizeRequest(BaseModel):
    article_text: str

    @field_validator('article_text')
    @classmethod
    def validate_article_text(cls, v):
        if not v or not v.strip():
            raise ValueError('article_text cannot be empty')
        return v


class SummarizeResponse(BaseModel):
    summary: str


class ErrorResponse(BaseModel):
    error: str


class RateBiasRequest(BaseModel):
    article_text: str

    @field_validator('article_text')
    @classmethod
    def validate_article_text(cls, v):
        if not v or not v.strip():
            raise ValueError('article_text cannot be empty')
        return v


class RateBiasResponse(BaseModel):
    scores: Dict[str, float]
    ai_model: str


app = FastAPI(
    title="Article Summarization Service",
    description="AI-powered article summarization using Gemini",
    version="1.0.0"
)


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
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY not configured"
        )

    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"
        
        prompt = f"""Summarize the following news article in 2-3 concise sentences. 
Focus on the key facts and main points:

{article_text}"""
        
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
            model=model, 
            contents=contents, 
            config=generate_content_config
        )
        
        summary_text = (result.text or "").strip()
        
        if not summary_text:
            raise RuntimeError("Empty summary returned from model")
            
        return summary_text
        
    except HTTPException:
        # Re-raise our own HTTP exceptions
        raise
    except Exception as e:
        # Map any upstream/model errors to 502 Bad Gateway
        print(f"Error calling Gemini API: {str(e)}")
        raise HTTPException(
            status_code=502, 
            detail="Summary generation failed"
        )


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "summarization"}


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        502: {"model": ErrorResponse, "description": "Upstream service failure"}
    }
)
def summarize(payload: SummarizeRequest):
    """
    Generate a concise summary of the provided article text.
    
    - **article_text**: The full text of the article to summarize (required, non-empty)
    
    Returns a JSON object with a 'summary' field containing the generated summary.
    """
    summary = summarize_with_gemini(payload.article_text)
    return SummarizeResponse(summary=summary)


@app.post(
    "/rate-bias",
    response_model=RateBiasResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Server configuration error"},
        502: {"model": ErrorResponse, "description": "Upstream service failure"}
    }
)
async def rate_bias(payload: RateBiasRequest):
    """
    Analyze an article for political bias across multiple dimensions.
    
    Makes N parallel LLM calls (one per bias dimension) and returns compiled scores.
    The endpoint is atomic: if any dimension analysis fails, the entire request fails.
    
    - **article_text**: The full text of the article to analyze (required, non-empty)
    
    Returns a JSON object with:
    - **scores**: Dictionary mapping dimension names to scores (1.0-7.0)
    - **model_used**: The AI model used for analysis
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
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured"
        )
    
    # Execute parallel LLM calls for all dimensions
    try:
        raw_scores = await rate_bias_parallel(
            payload.article_text,
            dimension_configs,
            model
        )
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 502 from rate_bias_parallel)
        raise
    except Exception as e:
        # Catch any unexpected errors
        print(f"Unexpected error in bias rating: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Bias rating failed: {str(e)}"
        )
    
    # Apply scoring function (currently pass-through)
    final_scores = score_bias(raw_scores)
    
    return RateBiasResponse(
        scores=final_scores,
        ai_model=model
    )

