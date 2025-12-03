# Project Name: Veritas News

## Members: Jack Webster, Aadity Sharma, Yann Calvo-Lopez, Vineet Jammalamadaka

## Google Drive Link: https://drive.google.com/drive/folders/16DhHYGhWOP0-UIXO258NQ7Z6VN5TJmlq?usp=drive_link

## 📚 Documentation

For comprehensive documentation including setup, testing, and implementation details, see the **[docs/](docs/)** folder:

- **[docs/INDEX.md](docs/INDEX.md)** - Start here! Complete documentation index
- **[docs/guides/EXAMINER.md](docs/guides/EXAMINER.md)** - For examiners and code reviewers
- **[docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)** - Quick setup and testing
- **[docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md)** - Implementation checklist
- **[docs/implementation/](docs/implementation/)** - Detailed implementation documentation
- **[docs/testing/](docs/testing/)** - Testing scenarios and troubleshooting

### Project Overview
News aggregation and synthesis platform to deliver real time updates on world news while highlighting differing perspectives and potential biases. 

The core features of our application will include a news feed which will aggregate news articles through web scraping / api integration and provide an estimated bias rating and a summary of differing perspectives for each news topic. The application will also provide references / links to primary sources when relevant to indicate potential misinformation or contradictory information. 

Additionally the product will allow users to open any news article within the context of the application, to gain further insight into the potential bias of the article and engage with other articles on the topic.  
To standardize scoring, the application will ask an LLM / API to consider a set of core questions, for example: 
Does the article implicitly or explicitly support positions associated with progressive or conservative policy agendas? (What language / quotes support this)
Does the article use emotionally charged wording in favor of one side?
Issue emphasis: Which issues are prioritized (e.g., immigration, climate, taxation), and how are they framed? (What language / quotes support this?)
Does the article portray any underlying values (individual freedom, social justice, tradition, markets) more aligned with one end of the spectrum?

## Setup & Installation

### Prerequisites
- Python 3.11+
- pip or conda
- Google Gemini API key (get it at https://aistudio.google.com/app/apikey)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/cs1060f25/veritasnews-project.git
   cd veritasnews-project
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

## Running the Application

### 1. Start the Main Backend API

```bash
cd veritasnews-project
source venv/bin/activate
export GEMINI_API_KEY="your-key-here"
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`
- Docs: http://localhost:8001/docs
- Bias Ratings: http://localhost:8001/bias_ratings/
- Summarize: POST http://localhost:8001/bias_ratings/summarize

### 3. Test the Summarization Endpoint

```bash
curl -X POST http://localhost:8001/bias_ratings/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Your long article text here..."
  }'
```

## Running Tests

### Unit Tests
```
python -m pytest tests/test_summarization.py -v
```

### Integration Tests
```
python -m pytest tests/ -v
```

### Test with Coverage
```
python -m pytest tests/ --cov=src --cov-report=html
```

## Architecture

### Services

1. **Main Backend API** (`src/`)
   - FastAPI application for managing bias ratings and articles
   - Includes AI library (`src/ai/`) for summarization and bias analysis
   - Calls Google Gemini API directly via the AI library
   - Database: SQLite with articles and bias ratings tables
   - Worker: Background news scraping and processing

### Project Structure

```
veritasnews-project/
├── src/
│   ├── ai/                     # AI library (summarization & bias analysis)
│   │   ├── summarization.py
│   │   ├── bias_analysis.py
│   │   ├── config.py
│   │   ├── scoring.py
│   │   └── prompts.yaml
│   ├── api/                    # FastAPI routes
│   │   └── routes_bias_ratings.py
│   ├── db/                     # Database operations
│   │   ├── init_db.py
│   │   └── bias_rating_db.py
│   ├── worker/                 # Article fetching & processing
│   │   ├── pipeline.py
│   │   ├── fetchers.py
│   │   ├── news_worker.py
│   │   └── scheduler.py
│   ├── models/                 # Data models
│   │   └── bias_rating.py
│   └── main.py                 # FastAPI app entry point
├── tests/                      # Test suite
│   ├── test_bias_ratings.py
│   ├── test_init_db.py
│   ├── test_summarization.py
│   ├── test_ai_summarization.py
│   ├── test_ai_bias_analysis.py
│   └── test_e2e_backend.py
├── requirements.txt
├── .env.example
└── IMPLEMENTATION_PLAN.md
```

## Configuration

All configuration is managed via environment variables. See `.env.example` for available options:

- `DB_PATH`: Path to SQLite database
- `GEMINI_API_KEY`: Google Gemini API key (required for AI features)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `API_HOST` / `API_PORT`: API server configuration
- `WORKER_ENABLED`: Enable background worker
- `WORKER_SCHEDULE_INTERVAL`: How often worker runs (seconds)

## Development Notes

### Feature Branches

We follow the feature branch workflow:
1. Create feature branch: `git checkout -b feature/VERITAS-XX-description`
2. Commit frequently: `git commit -m "message [VERITAS-XX]"`
3. Rebase on main: `git rebase origin/main`
4. Merge: `git merge --no-ff feature/VERITAS-XX-description`

### Linear Integration

All work is tracked in Linear. Commit messages must include the Linear ticket ID (e.g., `[VERITAS-42]`) to auto-link commits to tickets.

## Troubleshooting

### GEMINI_API_KEY not configured
- Ensure you've set the `GEMINI_API_KEY` environment variable
- Export it before starting the backend: `export GEMINI_API_KEY="your-key"`
- Verify the key is valid at https://aistudio.google.com/app/apikey
- The AI library (`src/ai/`) requires this key for summarization and bias analysis



### Database errors
- Delete `veritas_news.db` to reset
- Database will be recreated on next run
- Check `DB_PATH` environment variable points to correct location