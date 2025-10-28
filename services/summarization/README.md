# Article Summarization Service

FastAPI microservice that provides AI-powered article summarization using Google's Gemini API.

## Features

- RESTful API endpoint for article summarization
- Integration with Google Gemini Flash model
- Input validation and error handling
- Comprehensive test suite

## Setup

### Prerequisites

- Python 3.11+
- Google Gemini API key

### Installation

1. **IMPORTANT**: This service reads the `.env` file from the **project root** (not from this directory).
   
   Create or edit `/path/to/veritasnews-project/.env` (the parent project directory) and add:
   ```
   GEMINI_API_KEY=your-actual-api-key-here
   ```

2. Install dependencies:
```bash
cd services/summarization
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note**: The service automatically loads `GEMINI_API_KEY` from the project root `.env` file. You do NOT need to create a separate `.env` file in this directory.

### Running the Service

Development mode:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

With Docker:
```bash
docker build -t summarization-service .
docker run -p 8000:8000 -e GEMINI_API_KEY="your-key" summarization-service
```

## API Documentation

Once running, visit:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Endpoints

#### `GET /`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "summarization"
}
```

#### `POST /summarize`
Generate a summary of article text.

**Request:**
```json
{
  "article_text": "Your article text here..."
}
```

**Response (200):**
```json
{
  "summary": "A concise summary of the article."
}
```

**Error Responses:**
- `400`: Invalid input (empty article_text)
- `500`: Server configuration error (missing API key)
- `502`: Upstream service failure (Gemini API error)

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=main --cov-report=html
```

## Example Usage

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Breaking news: Scientists have discovered a new species of butterfly in the Amazon rainforest. The colorful insect, named Morpho amazonica, features iridescent blue wings and is believed to be endemic to a small region near the Peruvian border."
  }'
```

## Architecture

- **Framework**: FastAPI for high-performance async API
- **LLM Provider**: Google Gemini 2.0 Flash
- **Validation**: Pydantic models for request/response validation
- **Error Handling**: Graceful degradation with appropriate HTTP status codes

## Development

### Code Structure

```
services/summarization/
├── main.py              # FastAPI application and endpoints
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── README.md           # This file
└── tests/
    └── test_summarize.py  # Test suite
```

### Adding Features

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make changes and add tests
3. Run tests: `pytest`
4. Commit with Linear ID: `git commit -m "feat: description [VERITAS-XX]"`

## License

Part of the VeritasNews project.

