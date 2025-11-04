# Manual Testing Guide for Bias Scoring

## Prerequisites

1. **Activate virtual environment:**
   ```bash
   cd services/summarization
   source venv/bin/activate
   ```

2. **Ensure API key is set:**
   ```bash
   # Check if .env exists in project root
   ls ../../.env
   
   # Or verify environment variable is loaded
   echo $GEMINI_API_KEY
   ```

## Step 1: Start the Server

**Development mode (with auto-reload):**
```bash
cd services/summarization
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode (no reload):**
```bash
cd services/summarization
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server will start and you'll see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Keep this terminal open** - the server runs in the foreground.

## Step 2: Test the Endpoint (in a NEW terminal)

Open a **new terminal window** and run:

### Test 1: Health Check
```bash
curl http://localhost:8000/
```

Expected response:
```json
{"status":"ok","service":"summarization"}
```

### Test 2: Rate Bias Endpoint
```bash
curl -X POST http://localhost:8000/rate-bias \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "The Senate passed a new bill today with bipartisan support. The legislation aims to address climate change through renewable energy incentives."
  }'
```

Expected response:
```json
{
  "scores": {
    "partisan_bias": 4.0,
    "affective_bias": 1.0,
    "framing_bias": 4.0,
    "sourcing_bias": 5.0
  },
  "ai_model": "gemini-2.5-flash"
}
```

### Test 3: Pretty Print JSON (using jq)
```bash
curl -X POST http://localhost:8000/rate-bias \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "The Senate passed a new bill today with bipartisan support."
  }' | jq .
```

### Test 4: Test with a Longer Article
```bash
curl -X POST http://localhost:8000/rate-bias \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Congressional leaders announced a groundbreaking bipartisan agreement today that would reshape the nation'\''s approach to healthcare reform. Republican Senator John Smith and Democratic Representative Jane Doe praised the legislation, calling it a historic compromise. However, some progressive groups criticized the bill as insufficient, while conservative think tanks expressed concerns about government overreach. The bill includes provisions for expanded Medicaid coverage, prescription drug price controls, and incentives for preventive care. Analysts predict the legislation will face significant challenges in both chambers."
  }' | jq .
```

### Test 5: Test Error Handling (Empty Text)
```bash
curl -X POST http://localhost:8000/rate-bias \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": ""
  }'
```

Expected: `422` status code (validation error)

## Step 3: Interactive API Documentation

While the server is running, open your browser to:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test the endpoint directly from the browser interface!

## Step 4: Using Python httpx (Alternative)

If you prefer Python (uses httpx which is already installed):

```bash
cd services/summarization
source venv/bin/activate
python3 << 'EOF'
import httpx
import json

url = "http://localhost:8000/rate-bias"
article = "The Senate passed a new bill today with bipartisan support."

response = httpx.post(
    url,
    json={"article_text": article},
    timeout=60.0
)

print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
EOF
```

## Step 5: Stop the Server

In the terminal where the server is running, press:
```
Ctrl+C
```

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Kill existing process: `kill -9 <PID>` or use different port: `--port 8001`

### Getting 500 errors
- Check that `GEMINI_API_KEY` is set in `.env` file at project root
- Verify `.env` file exists: `ls ../../.env`

### Getting 502 errors
- Check your Gemini API key is valid
- Check your internet connection
- The API might be rate-limited (wait a few seconds)

### See server logs
The server logs will show:
- Each incoming request
- Any errors
- API call status

