# Quick Start Guide: AI Article Summarization

This guide walks you through setting up and testing the summarization feature (VERITAS-42 and VERITAS-43).

## Prerequisites
- Python 3.11+
- A Google Gemini API key (free from https://aistudio.google.com/app/apikey)
- Git

## Step 1: Get Your Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key" 
3. Copy the generated key
4. Save it somewhere safe (you'll need it soon)

## Step 2: Clone and Setup

```bash
# Clone the repo
git clone https://github.com/cs1060f25/veritasnews-project.git
cd veritasnews-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Setup the Main Backend API

```bash
cd /path/to/veritasnews-project

# Activate your venv (from Step 2)
source venv/bin/activate

# Set your Gemini API key
export GEMINI_API_KEY="paste-your-key-here"

# Start the backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

✅ Backend API is running at http://localhost:8001

The backend now includes the AI library (`src/ai/`) which handles summarization and bias analysis directly - no separate service needed!

## Step 4: Test the Summarization Endpoint

Open a **third terminal** and run:

```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Breaking news: Scientists have discovered a new species of butterfly in the Amazon rainforest. The colorful insect, named Morpho amazonica, features iridescent blue wings and is believed to be endemic to a small region near the Peruvian border. According to Dr. Maria Silva from the Brazilian Institute of Biology, this discovery is significant because it suggests the presence of undocumented ecosystems within the rainforest. The research team spent three months conducting field studies and collecting specimens. Conservation efforts are already underway to protect the species habitat. The butterfly has attracted international attention from the scientific community, with researchers planning to conduct DNA analysis to determine its evolutionary relationship to other Morpho species."
  }'
```

**Expected response:**
```json
{
  "summary": "Scientists have discovered a new butterfly species named Morpho amazonica in the Amazon rainforest with iridescent blue wings, suggesting undocumented ecosystems exist in the region. The Brazilian research team conducted three-month field studies and is pursuing conservation efforts and DNA analysis to understand the species' evolutionary background."
}
```

✅ Summarization is working!

## Step 5: Test the Bias Analysis Endpoint

**Note:** Bias analysis requires an article to exist in the database first. You'll need to create an article or use an existing one.

### Option A: Test with an existing article (if you have articles in your database)

```bash
# First, check what articles exist (if you have a GET endpoint)
# Or create an article via your worker/API

# Then analyze it for bias
curl -X POST http://localhost:8001/bias_ratings/analyze \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'
```

**Expected response:**
```json
{
  "rating_id": 1,
  "article_id": 1,
  "bias_score": 0.0,
  "reasoning": "",
  "scores": {
    "partisan_bias": 4.0,
    "affective_bias": 3.5,
    "framing_bias": 4.2,
    "sourcing_bias": 5.0
  }
}
```

### Option B: Create an article first, then analyze it

```bash
# Step 1: Create an article (example - adjust based on your article creation endpoint)
# This is just an example - you may need to use your actual article creation endpoint

# Step 2: Analyze the article for bias
curl -X POST http://localhost:8001/bias_ratings/analyze \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'
```

**What the bias analysis returns:**
- `scores`: A dictionary with 4 bias dimensions, each scored 1.0-7.0:
  - `partisan_bias`: Explicit political alignment (1=Left, 4=Neutral, 7=Right)
  - `affective_bias`: Emotional language intensity (1=Neutral, 7=Highly emotional)
  - `framing_bias`: Narrative framing perspective (1=Left-leaning, 4=Balanced, 7=Right-leaning)
  - `sourcing_bias`: Source diversity (1=One-sided, 7=Wide diversity)
- `bias_score`: Currently returns 0.0 (single composite score not yet implemented)
- `rating_id`: Database ID of the stored rating

✅ Bias analysis is working!

## Step 6: Run Tests

In your main terminal:

```bash
# Test the AI library functions
pytest tests/test_ai_summarization.py -v
pytest tests/test_ai_bias_analysis.py -v

# Test the backend integration
pytest tests/test_summarization.py -v

# Run all tests
pytest tests/ -v
```

**Expected output:**
```
tests/test_summarization.py::TestSummarizationEndpoint::test_summarize_missing_article_text PASSED
tests/test_summarization.py::TestSummarizationEndpoint::test_summarize_empty_article_text PASSED
tests/test_summarization.py::TestSummarizationIntegration::test_api_health PASSED
...
```

## Testing Different Scenarios

### Scenario 1: Empty Article (Should fail gracefully)
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{"article_text": ""}'
```
Expected: 422 Unprocessable Entity

### Scenario 2: No Article Text (Should fail gracefully)
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{}'
```
Expected: 422 Unprocessable Entity

### Scenario 3: Missing API Key (Should handle gracefully)
1. Stop the backend (Ctrl+C)
2. Start without GEMINI_API_KEY:
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```
3. Run this curl:
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{"article_text": "Your article here..."}'
```
Expected: 500 Internal Server Error with "GEMINI_API_KEY not configured"

4. Restart with API key to continue testing

### Scenario 4: Very Long Article
```bash
# Create a file with a long article
cat > sample_article.txt << 'ENDTEXT'
[Your very long article text here - the longer the better for testing]
Lorem ipsum dolor sit amet, consectetur adipiscing elit...
[Continue with more text...]
ENDTEXT

# Test with it
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d @sample_article.json
```

## API Documentation

### Health Check
```bash
curl http://localhost:8001/  # Main backend
```

### Interactive API Docs
- Main Backend: http://localhost:8001/docs

## Troubleshooting

### Issue: "GEMINI_API_KEY not configured" error
**Solution:** Set the environment variable before starting the backend
```bash
export GEMINI_API_KEY="your-actual-key"
# Then restart the backend
```

### Issue: Timeout errors
**Solution:** The Gemini API might be slow. Try with a shorter article first.

### Issue: "502 Bad Gateway" or "Upstream service failure"
**Solution:** 
1. Check that GEMINI_API_KEY is set correctly
2. Verify the API key is valid at https://aistudio.google.com/app/apikey
3. Check backend logs for detailed error messages

## Architecture Overview

```
┌─ Backend API (Port 8001) ───────────────────────┐
│ Main FastAPI Application                        │
│ ├─ POST /bias_ratings/summarize                │
│ ├─ POST /bias_ratings/analyze                  │
│ ├─ GET /bias_ratings/                          │
│ └─ GET /  (health check)                       │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ AI Library (src/ai/)                       │ │
│ │ ├─ summarization.py → Gemini API           │ │
│ │ ├─ bias_analysis.py → Gemini API           │ │
│ │ └─ config.py (prompts.yaml)                │ │
│ └────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────┘
                       ▲
                       │
                       │ (HTTP requests)
                       │
         ┌─ Your client
         │ ├─ curl / Postman / Web Browser
         │ └─ pytest / Integration tests
         └──────────────────────────────────────
```

## Next Steps

1. **Integration**: Add summarization to the article pipeline
2. **UI**: Create a frontend component to display summaries
3. **Database**: Store summaries in the database
4. **Optimization**: Add caching and rate limiting
5. **Monitoring**: Set up production metrics

## Files to Review

- 📄 `docs/implementation/` - Implementation plans and summaries
- 📄 `README.md` - Comprehensive documentation
- 📁 `src/ai/` - AI library (summarization & bias analysis)
- 📁 `src/api/` - Backend API routes
- 📁 `tests/` - Test suites

## Getting Help

- Check the README.md for detailed setup and troubleshooting
- Review the inline code comments for implementation details
- Look at the test files to see how the API is used

## Success Indicators

✅ You've successfully completed the setup when you see:
- [ ] Backend API running on http://localhost:8001
- [ ] Successful summarization request returns a summary
- [ ] Error handling works (missing API key, invalid input, etc.)
- [ ] Tests pass: `pytest tests/test_summarization.py -v`
- [ ] AI library tests pass: `pytest tests/test_ai_summarization.py -v`

**Great job! The AI Article Summarization feature is ready to use!** 🎉
