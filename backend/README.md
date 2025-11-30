# Veritas News Backend

AI-powered news aggregation and political bias analysis API built with FastAPI.

## Features

- **News Aggregation**: Fetches news from multiple sources (NewsAPI, RSS feeds, web scraping)
- **Bias Analysis**: AI-powered political bias detection using multiple dimensions:
  - Partisan bias
  - Affective bias
  - Framing bias
  - Sourcing bias
- **Article Summarization**: Generates AI summaries using Google Gemini
- **RESTful API**: FastAPI-based endpoints for frontend integration

## Requirements

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

### Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --dev

# Run the server
uv run uvicorn veritas_news.main:app --reload

# Or use the CLI
uv run veritas-news
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run the server
uvicorn veritas_news.main:app --reload
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
# NewsAPI Key (for news fetching)
NEWSAPI_KEY=your_newsapi_key

# Google Gemini API Key (for AI summarization)
GEMINI_API_KEY=your_gemini_key

# Worker Configuration
WORKER_ENABLED=true
WORKER_USE_NEWSAPI=false
WORKER_USE_CNN=false
WORKER_HOURS_BACK=1
WORKER_LIMIT=5
WORKER_SCHEDULE_INTERVAL=1800
```

## API Endpoints

### Articles

- `GET /articles/latest` - Get latest articles with bias ratings
  - Query params: `limit`, `offset`, `min_bias_score`, `max_bias_score`

### Bias Ratings

- `POST /bias_ratings/analyze` - Analyze article for political bias
- `POST /bias_ratings/summarize` - Generate AI summary for article text

### Health

- `GET /` - API health check

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black src tests
uv run isort src tests

# Lint
uv run ruff check src tests

# Type check
uv run mypy src
```

## Project Structure

```
backend/
├── pyproject.toml        # Project configuration
├── src/
│   └── veritas_news/
│       ├── __init__.py
│       ├── main.py       # FastAPI application
│       ├── ai/           # AI/ML modules (bias analysis, summarization)
│       ├── api/          # API route handlers
│       ├── db/           # Database models and utilities
│       ├── models/       # Pydantic/SQLAlchemy models
│       └── worker/       # Background worker for news fetching
├── scripts/              # Utility scripts
│   └── refresh_database.py  # Database management tool
└── tests/                # Test files
```

## Database Management

The `scripts/refresh_database.py` script provides utilities to manage the database for development and testing.

### Quick Start for New Developers

```bash
# Set up a fresh database with articles and bias analysis
uv run python scripts/refresh_database.py --full --limit 15
```

### Available Commands

```bash
# Show current database status
uv run python scripts/refresh_database.py --status

# Initialize fresh database (drops existing data)
uv run python scripts/refresh_database.py --init

# Fetch new articles from RSS feeds
uv run python scripts/refresh_database.py --fetch --limit 20

# Analyze bias for articles without ratings
uv run python scripts/refresh_database.py --analyze

# Remove articles older than 7 days
uv run python scripts/refresh_database.py --cleanup --days 7

# Full refresh: init + fetch + analyze
uv run python scripts/refresh_database.py --full

# Verify database integrity
uv run python scripts/refresh_database.py --verify
```

### Daily Refresh (Recommended)

To keep the database fresh with current news:

```bash
# Option 1: Full refresh (clears old data)
uv run python scripts/refresh_database.py --full --limit 15

# Option 2: Add new articles without clearing
uv run python scripts/refresh_database.py --fetch --analyze --cleanup --days 3
```

## License

MIT

