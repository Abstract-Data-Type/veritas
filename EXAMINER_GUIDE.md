# Examiner Guide: AI Article Summarization Feature (VERITAS-42 & VERITAS-43)

This guide explains how to review and test the implemented summarization feature.

## Quick Summary

**What was implemented:**
- **VERITAS-42**: FastAPI microservice that calls Google Gemini API to summarize articles
- **VERITAS-43**: Integration of the microservice into the main backend API

**Architecture:**
```
Backend API (port 8001)
    ↓
POST /bias_ratings/summarize
    ↓
Calls Summarization Service (port 8000)
    ↓
Gemini API
    ↓
Returns summary
```

## How to Test

### Prerequisites
1. **Python 3.11+** installed
2. **Gemini API Key** - Get a free key from https://aistudio.google.com/app/apikey
3. **Clone the repo** and navigate to the project root

### Step 1: Set Up Environment Variables

The project root should have a `.env` file with:
```
GEMINI_API_KEY=your-actual-key-here
SUMMARIZATION_SERVICE_URL=http://localhost:8000
```

If missing, create it:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Step 2: Install Dependencies

**Backend dependencies** (in main venv):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Microservice dependencies** (separate venv):
```bash
cd services/summarization
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ../..
```

### Step 3: Run Both Services

**Terminal 1 - Summarization Microservice:**
```bash
cd services/summarization
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Terminal 2 - Backend API:**
```bash
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```
Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

### Step 4: Test the Endpoint

**Terminal 3 - Test request:**
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
  "summary": "Scientists have discovered a new butterfly species in the Amazon with distinctive blue wings, suggesting the presence of undocumented ecosystems. Conservation efforts are underway as researchers plan DNA analysis to understand the species' evolutionary background."
}
```

## Testing Different Scenarios

### Test 1: Empty Article (Should fail with 400)
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{"article_text": ""}'
```
Expected: `422 Unprocessable Entity`

### Test 2: Missing Article Text (Should fail with 400)
```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{}'
```
Expected: `422 Unprocessable Entity`

### Test 3: Service Unavailable (Should fail gracefully)
1. Stop the summarization service (Ctrl+C in Terminal 1)
2. Make the same request
3. You should get: `{"detail":"Cannot reach summarization service"}` with status 502
4. Restart the service to continue testing

### Test 4: Health Check
```bash
curl http://localhost:8000/  # Summarization service
curl http://localhost:8001/  # Backend API
```
Both should return status 200 with `{"status":"ok"}`

## Interactive API Documentation

Both services have interactive Swagger docs:
- **Summarization Service**: http://localhost:8000/docs
- **Backend API**: http://localhost:8001/docs

Use these to explore endpoints and test interactively.

## Code Review: What to Look At

### VERITAS-42: Summarization Microservice

**Files:**
- `services/summarization/main.py` - Core implementation
- `services/summarization/requirements.txt` - Dependencies
- `services/summarization/tests/test_summarize.py` - Unit tests
- `services/summarization/Dockerfile` - Container config
- `services/summarization/README.md` - Service docs

**Key features:**
- ✅ Loads GEMINI_API_KEY from environment or `.env`
- ✅ Input validation (non-empty article required)
- ✅ Error handling (500 for missing key, 502 for API failures)
- ✅ Uses Pydantic for request/response models
- ✅ Comprehensive unit tests with mocking

### VERITAS-43: Backend Integration

**Files:**
- `src/api/routes_bias_ratings.py` - Endpoint implementation (lines 163-229)
- `src/worker/pipeline.py` - Helper method for summarization (lines 17-56)
- `tests/test_summarization.py` - Integration tests
- `README.md` - Updated with setup instructions

**Key features:**
- ✅ Async endpoint for non-blocking calls
- ✅ Configurable service URL via environment variable
- ✅ Proper error mapping (502, 504 for upstream failures)
- ✅ Graceful degradation if service unavailable
- ✅ Integration tests included

## Git Workflow Review

**Feature branch:** `feature/VERITAS-43-integrate-summarization`

**Commits** (in order):
1. `c8b8b77` - VERITAS-42: FastAPI summarization service with Gemini
2. `92ecd77` - VERITAS-43: Add summarization endpoint integration
3. `d603a26` - VERITAS-43: Add setup and troubleshooting guide
4. `dc29b02` - VERITAS-43: Add comprehensive implementation summary
5. `43100e3` - VERITAS-43: Add quick start guide
6. `a1a71e4` - VERITAS-43: Add troubleshooting guide
7. `d288453` - VERITAS-42: Add python-dotenv support
8. `82a2ab0` - VERITAS-43: Update service to load .env

**All commits include Linear ticket IDs** as required.

## Verification Checklist

✅ Both services start without errors  
✅ Services respond to health checks (port 8000 and 8001)  
✅ Summarization endpoint returns proper summaries  
✅ Input validation works (rejects empty articles)  
✅ Error handling works (graceful 502 when service down)  
✅ Tests pass: `pytest tests/test_summarization.py -v`  
✅ Tests pass: `cd services/summarization && pytest tests/ -v`  
✅ Code follows best practices (async, error handling, validation)  
✅ Documentation is comprehensive and clear  
✅ Git commits follow workflow correctly  

## Troubleshooting

### "Address already in use" on port 8000 or 8001
```bash
# Kill processes on that port
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
lsof -i :8001 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### "GEMINI_API_KEY not configured"
- Check `.env` file exists in project root
- Check it contains: `GEMINI_API_KEY=your-actual-key`
- Restart the summarization service after editing `.env`

### Service returns "Cannot reach summarization service"
- Check summarization service is running on port 8000
- Check `SUMMARIZATION_SERVICE_URL=http://localhost:8000` in `.env`
- Try: `curl http://localhost:8000/`

### Timeout errors
- Gemini API might be slow, try with shorter article
- Check network connectivity
- Verify API key is valid at https://aistudio.google.com/app/apikey

## Architecture Decisions

**Why microservices?**
- Separation of concerns: API layer separate from LLM integration
- Scalability: Can scale summarization service independently
- Testability: Easy to mock in integration tests
- Maintainability: Each service has clear responsibility

**Why async?**
- Non-blocking I/O: Backend doesn't wait for LLM response
- Better resource usage: Multiple requests can be processed concurrently
- Scalability: Handle more concurrent requests

**Why error handling?**
- Graceful degradation: App doesn't crash if Gemini is down
- Clear error messages: Clients know what went wrong
- Proper HTTP status codes: 502 for upstream, 504 for timeout

## Files Structure

```
veritasnews-project/
├── services/
│   └── summarization/          # Microservice
│       ├── main.py             # FastAPI app
│       ├── requirements.txt    # Dependencies
│       ├── Dockerfile          # Container config
│       ├── README.md           # Service docs
│       └── tests/
│           └── test_summarize.py
├── src/
│   ├── api/
│   │   └── routes_bias_ratings.py   # /summarize endpoint
│   ├── worker/
│   │   └── pipeline.py              # Helper method
│   └── main.py                      # FastAPI app
├── tests/
│   └── test_summarization.py        # Integration tests
├── .env                             # Configuration (not in git)
├── requirements.txt                 # Backend dependencies
├── README.md                        # Main project docs
├── IMPLEMENTATION_PLAN.md           # Original plan
├── IMPLEMENTATION_SUMMARY.md        # What was built
├── QUICK_START.md                   # Quick start guide
└── EXAMINER_GUIDE.md               # This file
```

## Summary

The implementation is **complete, tested, and working**. Both VERITAS-42 and VERITAS-43 are integrated and functional. The feature branch is ready to be merged into main after review.

**To verify:** Follow Steps 1-4 above and run the test requests. You should see working summaries being generated by the Gemini API.

Thank you for reviewing! 🎉
