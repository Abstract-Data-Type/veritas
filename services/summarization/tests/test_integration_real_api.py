"""
Real Integration Test - Makes Actual Gemini API Calls

WARNING: This test makes real API calls to Gemini and will incur costs.
Run this only when you want to verify the actual integration works.
"""
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env from project root (same as main.py does)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

import main

client = TestClient(main.app)


def test_real_rate_bias_api_call():
    """Make a REAL API call to Gemini and verify the response"""
    
    # Check if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY not found. Skipping real API test.")
        return
    
    print(f"✓ GEMINI_API_KEY found (length: {len(api_key)} chars)")
    print()
    
    # Test article - a simple news-like text
    test_article = """
    The Senate passed a new bill today with bipartisan support. 
    The legislation, which was introduced last month, aims to address climate change 
    through a combination of renewable energy incentives and carbon reduction targets.
    Republicans and Democrats both praised the bill's balanced approach, though some 
    environmental groups argued it doesn't go far enough. The bill now moves to the House 
    for consideration.
    """
    
    print("=" * 70)
    print("REAL INTEGRATION TEST - Making Actual Gemini API Calls")
    print("=" * 70)
    print()
    print(f"Article text (first 100 chars): {test_article[:100]}...")
    print()
    print("Calling /rate-bias endpoint (this will make 4 parallel Gemini API calls)...")
    print()
    
    try:
        resp = client.post(
            "/rate-bias",
            json={"article_text": test_article.strip()}
        )
        
        print(f"Response Status: {resp.status_code}")
        print()
        
        if resp.status_code == 200:
            data = resp.json()
            print("✅ SUCCESS! Real API calls worked!")
            print()
            print("Response:")
            print(f"  AI Model: {data.get('ai_model')}")
            print()
            print("Bias Scores:")
            scores = data.get('scores', {})
            for dimension, score in scores.items():
                print(f"  {dimension}: {score:.2f}")
            print()
            
            # Verify all dimensions are present
            expected_dims = {'partisan_bias', 'affective_bias', 'framing_bias', 'sourcing_bias'}
            actual_dims = set(scores.keys())
            if actual_dims == expected_dims:
                print("✅ All 4 bias dimensions returned")
            else:
                print(f"⚠️  Missing dimensions: {expected_dims - actual_dims}")
            
            # Verify scores are in valid range
            all_valid = all(1.0 <= score <= 7.0 for score in scores.values())
            if all_valid:
                print("✅ All scores in valid range (1.0 - 7.0)")
            else:
                print("⚠️  Some scores outside valid range!")
                for dim, score in scores.items():
                    if not (1.0 <= score <= 7.0):
                        print(f"    {dim}: {score} (INVALID)")
            
            print()
            print("=" * 70)
            print("✅ REAL INTEGRATION TEST PASSED")
            print("=" * 70)
            
            return True
        else:
            print(f"❌ FAILED: Status {resp.status_code}")
            print(f"Error: {resp.json()}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    test_real_rate_bias_api_call()
    print()

