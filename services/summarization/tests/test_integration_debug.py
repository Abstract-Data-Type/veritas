"""
Debug Integration Test - Detailed output of what's happening
"""
import os
import sys
from pathlib import Path

# Load .env
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found")
    sys.exit(1)

print(f"✓ API Key found: {api_key[:10]}...{api_key[-5:]}")
print()

# Test with a simple direct call
client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"

test_prompt = """On a scale of 1-7, does this article's language, framing, and sourcing favor a political party or ideology?
1 = Strongly favors the Left
4 = Neutral / Balanced
7 = Strongly favors the Right

Respond with only a single number between 1 and 7.

Article text:
The Senate passed a new bill today with bipartisan support."""

print("Making direct Gemini API call...")
print(f"Model: {model}")
print(f"Prompt length: {len(test_prompt)} chars")
print()

try:
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=test_prompt)],
        )
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=20,
    )
    
    print("Calling generate_content...")
    result = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config
    )
    
    print(f"✓ API call succeeded!")
    print(f"Response type: {type(result)}")
    print(f"Response text: '{result.text}'")
    print(f"Response text type: {type(result.text)}")
    print(f"Response text length: {len(result.text) if result.text else 0}")
    
    if hasattr(result, 'candidates'):
        print(f"Has candidates: {hasattr(result, 'candidates')}")
        if hasattr(result, 'candidates') and result.candidates:
            print(f"Candidates count: {len(result.candidates)}")
            if result.candidates:
                print(f"First candidate: {result.candidates[0]}")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

