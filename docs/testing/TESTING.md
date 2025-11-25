# Testing the Summarization Feature

## Quick Setup

The backend now includes the AI library (`src/ai/`) which handles summarization directly - no separate service needed!

### Setup
```bash
cd /Users/yanncalvolopez/veritasnews-project
source venv/bin/activate
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

### Test the API
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{"article_text": "Your article text here"}'
```

## Running Tests

### Unit Tests (AI Library)
```bash
pytest tests/test_ai_summarization.py -v
pytest tests/test_ai_bias_analysis.py -v
```

### Integration Tests
```bash
pytest tests/test_summarization.py -v
pytest tests/test_bias_ratings.py -v
```

### End-to-End Tests
```bash
pytest tests/test_e2e_backend.py -v -m e2e
```

## Status

✅ Backend API: Running on port 8001
✅ Summarization Endpoint: Implemented at `/bias_ratings/summarize`
✅ AI Library: `src/ai/` handles summarization and bias analysis
✅ Error Handling: Working (returns 500 when API key missing, 502 for API failures)
✅ Tests: Comprehensive unit, integration, and e2e tests

The implementation is **complete** - just set `GEMINI_API_KEY` and start the backend!
