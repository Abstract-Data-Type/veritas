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

## Step 3: Setup the Summarization Microservice

Open a **new terminal** and run:

```bash
cd /path/to/veritasnews-project/services/summarization

# Create venv if needed
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key
export GEMINI_API_KEY="paste-your-key-here"

# Start the service
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

✅ Service is running at http://localhost:8000

## Step 4: Setup the Main Backend API

Open **another terminal** and run:

```bash
cd /path/to/veritasnews-project

# Activate your venv (from Step 2)
source venv/bin/activate

# Set environment variables
export SUMMARIZATION_SERVICE_URL=http://localhost:8000

# Start the backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

✅ Backend API is running at http://localhost:8001

## Step 5: Test the Summarization Endpoint

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

## Step 6: Run Tests

In your main terminal:

```bash
# Test the summarization service
cd services/summarization
pytest tests/test_summarize.py -v

# Test the backend integration
cd ../..
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

### Scenario 3: Service Down (Should handle gracefully)
1. Stop the summarization service (Ctrl+C in Terminal 1)
2. Run this curl:
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{"article_text": "Your article here..."}'
```
Expected: 502 Bad Gateway with error message

3. Restart the summarization service to continue testing

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
curl http://localhost:8000/  # Summarization service
curl http://localhost:8001/  # Main backend
```

### Interactive API Docs
- Summarization Service: http://localhost:8000/docs
- Main Backend: http://localhost:8001/docs

## Troubleshooting

### Issue: "Connection refused" when calling backend
**Solution:** Make sure the summarization service is running
```bash
# Check if service is running
curl http://localhost:8000/
```

### Issue: "GEMINI_API_KEY not configured" error
**Solution:** Set the environment variable before starting the service
```bash
export GEMINI_API_KEY="your-actual-key"
# Then restart the service
```

### Issue: Timeout errors
**Solution:** The Gemini API might be slow. Try with a shorter article first.

### Issue: "Cannot reach summarization service"
**Solution:** 
1. Check the service is running on port 8000
2. Check the `SUMMARIZATION_SERVICE_URL` is set correctly
3. Try: `curl http://localhost:8000/`

## Architecture Overview

```
┌─ Terminal 1 ─────────────────────────────────────┐
│ Summarization Microservice (Port 8000)           │
│ ├─ POST /summarize                              │
│ └─ GET /  (health check)                        │
└──────────────────────┬──────────────────────────┘
                       │
                       │ (async HTTP call)
                       │
┌─ Terminal 2 ─────────▼──────────────────────────┐
│ Main Backend API (Port 8001)                    │
│ ├─ POST /bias_ratings/summarize (VERITAS-43)   │
│ ├─ GET /bias_ratings/                          │
│ └─ GET /  (health check)                       │
└──────────────────────────────────────────────────┘
                       ▲
                       │
                       │ (HTTP requests)
                       │
         ┌─ Terminal 3 (Your client)
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

- 📄 `IMPLEMENTATION_PLAN.md` - Full technical specification
- 📄 `IMPLEMENTATION_SUMMARY.md` - What was implemented
- 📄 `README.md` - Comprehensive documentation
- 📁 `services/summarization/` - The microservice code
- 📁 `src/api/` - Backend API routes
- 📁 `tests/` - Test suites

## Getting Help

- Check the README.md for detailed setup and troubleshooting
- Review the inline code comments for implementation details
- Look at the test files to see how the API is used

## Success Indicators

✅ You've successfully completed the setup when you see:
- [ ] Summarization service running on http://localhost:8000
- [ ] Backend API running on http://localhost:8001
- [ ] Successful summarization request returns a summary
- [ ] Error handling works (service down, invalid input, etc.)
- [ ] Tests pass: `pytest tests/test_summarization.py -v`

**Great job! The AI Article Summarization feature is ready to use!** 🎉
