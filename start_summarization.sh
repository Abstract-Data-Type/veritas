#!/bin/bash
cd services/summarization
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null || pip install fastapi uvicorn google-genai httpx pydantic --quiet
export GEMINI_API_KEY="${GEMINI_API_KEY:-your-key-here}"
echo "🚀 Starting Summarization Service on port 8000..."
echo "📝 Set GEMINI_API_KEY if not already set"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
