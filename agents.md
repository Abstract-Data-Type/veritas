## Project Overview

## Project Name: News Aggregation and Bias Analysis Platform

## Summary:
This project is a news aggregation and synthesis platform that delivers real-time updates on world news while highlighting differing perspectives and potential biases. Core features include:

News Feed: Aggregates news articles through web scraping and API integration.

Bias & Perspective Analysis: Each article is assigned an estimated bias rating and a summary of differing perspectives.

Primary Sources: Provides references/links to indicate potential misinformation or contradictory information.

Contextual Reading: Users can open news articles within the app to gain insights on bias and engage with other articles on the same topic.

Standardized Scoring: Uses an LLM or API to answer core bias questions, such as:

Does the article implicitly or explicitly support progressive or conservative policy agendas?

Does the article use emotionally charged wording favoring one side?

Which issues are prioritized and how are they framed?

Does the article portray underlying values aligned with one end of the spectrum (individual freedom, social justice, tradition, markets)?

## System Design Overview:

   +-----------------+          HTTPS           +-----------------+
   |    React App    |  <----------------->   |   FastAPI API   |
   |  (Frontend)     |                          |  (Backend)     |
   +-----------------+                          +-----------------+
           |                                           |
           |                                           |
           |                                           |
           v                                           v
     Browser makes API calls                       SQLAlchemy ORM
           |                                           |
           v                                           v
   +-----------------+                        +-----------------+
   | Local / Managed |                        |  SQLite DB      |
   |  SQL Database   |                        | (development)  |
   | (Postgres prod) |                        | (app.db file)  |
   +-----------------+                        +-----------------+


## Components:

Frontend (React):

Displays news feed, bias ratings, and article details.

Communicates with backend API for data.

Backend (FastAPI):

Provides REST endpoints for bias ratings, news articles, and summaries.

Handles data validation, LLM/API calls, database interactions, and web scraping module
for aggregating / reading news articles. 

## Build and Test Commands

Backend:

# Install dependencies
pip install -r requirements.txt

# Run FastAPI locally
uvicorn backend.main:app --reload

# Run backend tests
pytest backend/tests

## Frontend:

# Install dependencies
cd frontend
npm install

# Run development server
npm start

# Build for production
npm run build

# Run frontend tests
npm test

## Code Style Guidelines

# Backend (Python):

Follow PEP8 and use type hints.

Use snake_case for variables/functions, PascalCase for classes.

Organize code into:

models.py → database models

schemas.py → Pydantic schemas

routers/ → API route definitions

database.py → DB connection

# Frontend (React/JSX):

Follow Airbnb JavaScript/React style guide.

Use functional components and hooks.

Keep components reusable and testable.

Use camelCase for variables/functions.

## Testing Instructions

Continuous Integration (CI):

CI runs automated tests on every pull request (PR).
CI ensures backend endpoints, frontend components, and integration flows are tested.
CI also runs linters and static analysis tools before allowing merges.

# Running Tests Locally:

Backend:
pytest /tests

Frontend:
cd frontend
npm test


# Linters / Static Analysis:

Python (backend):

flake8 src/


JavaScript/React (frontend):

cd frontend
eslint src/


# When to Update Tests:

- Add tests for new features or endpoints.
- Update existing tests only if the feature itself changes or if explicitly requested by project maintainers.
- Do NOT modify existing tests for unrelated code changes.