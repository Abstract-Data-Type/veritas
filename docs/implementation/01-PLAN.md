## Implementation Plan: Element + Interaction for AI Summarization

This document breaks the assignment into concrete tasks that any engineer can follow end‑to‑end. It selects:
- Element: Summarization microservice (FastAPI + Gemini)
- Interaction: Next.js API route in this app that calls the microservice and a simple UI trigger to display the summary for an article

References to read before starting:
- [Git Feature Branch Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow)
- [Merging vs Rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)


### Prerequisites
- Access to Linear workspace and project.
- Gemini API key stored as `GEMINI_API_KEY` (local `.env` or secret manager).
- GitHub access to this repository and permission to push feature branches.
- Node 18+ and Python 3.11+ installed locally (or Docker).


## Linear Issues to Create and Link

Create two feature issues and one bug issue (the bug will be created after you test). Put these IDs directly on the architecture diagram image (e.g., annotate in Figma or Preview) and commit that updated image under `docs/architecture/diagram.png`.

Where the template below says VERITAS-XXX, use your actual IDs after creating them in Linear.

### Feature 1 (Element): Build Summarization Service (FastAPI + Gemini)
- Title: "Summarization microservice: POST /summarize returns AI summary"
- ID: VERITAS-25 (example — replace with your actual ID)
- Background: We need a dedicated service to turn article text into a concise summary using an LLM.
- Description:
  - Implement a Python FastAPI service exposing `POST /summarize`.
  - Request body: `{ "article_text": string }` (non-empty).
  - Calls Gemini (model: `gemini-flash-latest`) to produce a short summary.
  - Response: `{ "summary": string }`.
  - Validate input; return 400 for missing/empty `article_text`.
  - Timeouts and robust error handling: return `502` with `{ "error": "Summary generation failed" }` on upstream failure.
  - Provide `Dockerfile` and `requirements.txt`.
  - Include unit tests with `pytest` and FastAPI `TestClient` covering: success, validation error, LLM failure (mocked).
- Dependencies:
  - Secrets: `GEMINI_API_KEY` available to the service.
  - Networking: reachable from the Next.js app (localhost or docker network).
  - Link to (or create) stub infra ticket(s) if needed for deployment.
- Basic Test Plan:
  - Unit tests: success path, 400, and mocked 502.
  - Manual: run `uvicorn` locally, cURL `POST /summarize` with a sample article; verify JSON response.
- Prompts/AI notes: Paste prompts you used to generate code into the Linear issue notes.
- Definition of Done:
  - Service starts locally; endpoint returns valid summary.
  - Tests passing locally (`pytest`).
  - Committed on feature branch with Linear ID in commit message.

### Feature 2 (Interaction): Next.js integration route and UI trigger
- Title: "Integrate summarization: Next.js API route + UI button"
- ID: VERITAS-22 (example — replace with your actual ID)
- Background: The web app needs to fetch summaries on demand.
- Description:
  - Add a Next.js route at `app/api/summarize/route.ts`.
  - Accept `POST` JSON `{ article_text }`; validate; call the summarization service; return `{ summary }`.
  - Configure service URL via `SUMMARIZATION_SERVICE_URL` (e.g., `http://localhost:8000`).
  - Add a minimal UI affordance (e.g., button) on an existing page (e.g., `components/TopicCard.js` or `app/topic/[id]/page.js`) to POST to `/api/summarize` and display the returned summary.
  - Keep UI changes minimal and accessible (focus states, ARIA live region for summary content).
- Dependencies:
  - Depends on Feature 1 service running locally.
  - If a real DB is not available, display summary in UI without persistence.
- Basic Test Plan:
  - Manual: from the page, click "Summarize"; confirm a summary renders, errors are handled with a toast.
  - Optional: add a simple integration test for the route handler (mock the backend call).
- Prompts/AI notes: Paste prompts into the Linear issue notes.
- Definition of Done:
  - API route returns summary via the service.
  - UI button triggers request and renders the result.
  - Commit includes Linear ID.

## Implementation Details

### A) Summarization Microservice (FastAPI + Gemini)

Proposed repo layout inside this repository for local development:

```
services/summarization/
  ├─ main.py
  ├─ requirements.txt
  ├─ Dockerfile
  ├─ tests/
  │   └─ test_summarize.py
  └─ README.md
```

Requirements (`requirements.txt`):
```
fastapi==0.115.0
uvicorn==0.30.6
google-genai==0.3.0
pytest==8.3.3
httpx==0.27.2
```

FastAPI skeleton (`main.py`):
```python
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types


class SummarizeRequest(BaseModel):
    article_text: str


app = FastAPI()


def summarize_with_gemini(article_text: str) -> str:
    if not article_text or not article_text.strip():
        raise HTTPException(status_code=400, detail="article_text is required")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-flash-latest"
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Summarize concisely:\n\n{article_text}")],
            )
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=8000),
        )

        # Use non-streaming for simplicity in a web handler
        result = client.models.generate_content(
            model=model, contents=contents, config=generate_content_config
        )
        text = (result.text or "").strip()
        if not text:
            raise RuntimeError("Empty summary from model")
        return text
    except HTTPException:
        raise
    except Exception:
        # Map any upstream/model errors to 502 as per requirements
        raise HTTPException(status_code=502, detail="Summary generation failed")


@app.post("/summarize")
def summarize(payload: SummarizeRequest):
    summary = summarize_with_gemini(payload.article_text)
    return {"summary": summary}
```

Run locally:
```bash
cd services/summarization
pip install -r requirements.txt
export GEMINI_API_KEY=... # set your key
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Unit tests (`tests/test_summarize.py`):
```python
import os
import pytest
from fastapi.testclient import TestClient
import main


client = TestClient(main.app)


def test_missing_article_text_returns_400():
    resp = client.post("/summarize", json={})
    assert resp.status_code == 422 or resp.status_code == 400  # Pydantic 422 vs guard 400


def test_llm_failure_returns_502(monkeypatch):
    def fail(_):
        raise Exception("upstream error")

    monkeypatch.setattr(main, "summarize_with_gemini", fail)
    resp = client.post("/summarize", json={"article_text": "Hello"})
    # The route returns whatever summarize_with_gemini raises; here it's generic Exception,
    # but our implementation maps to HTTPException(502) inside the function.
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Summary generation failed"


def test_success(monkeypatch):
    monkeypatch.setattr(main, "summarize_with_gemini", lambda _: "Short summary")
    resp = client.post("/summarize", json={"article_text": "Hello"})
    assert resp.status_code == 200
    assert resp.json() == {"summary": "Short summary"}
```

Optional Dockerfile (`Dockerfile`):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```


### B) Next.js Integration Route + Minimal UI

Environment variables (create `.env.local` at repo root):
```
SUMMARIZATION_SERVICE_URL=http://localhost:8000
```

Route handler (create `app/api/summarize/route.ts`):
```ts
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const articleText = (body?.article_text || "").trim();
    if (!articleText) {
      return NextResponse.json({ error: "article_text is required" }, { status: 400 });
    }

    const baseUrl = process.env.SUMMARIZATION_SERVICE_URL || "http://localhost:8000";
    const resp = await fetch(`${baseUrl}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ article_text: articleText }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      const message = data?.detail || data?.error || "Summary generation failed";
      return NextResponse.json({ error: message }, { status: 502 });
    }

    return NextResponse.json({ summary: data.summary });
  } catch (err) {
    return NextResponse.json({ error: "Unexpected error" }, { status: 500 });
  }
}
```

Minimal UI hook (example change site-wide or on `app/topic/[id]/page.js`):
- Add a "Summarize" button near article text.
- On click, `fetch('/api/summarize', { method: 'POST', body: JSON.stringify({ article_text }) })`.
- Render the `summary` into an ARIA live region for accessibility. Use `components/Toast.js` for errors.

Manual test steps:
- Start the Python service and the Next.js dev server.
- Open a topic/article page; click "Summarize"; confirm the text appears.
- Stop the Python service; click again; confirm a graceful error message.




## Rebasing, Squashing, and Merging
- Before merging each branch: `git checkout main && git pull --rebase origin main`, then `git rebase main` on your feature branch.
- Optionally clean up local history: `git rebase -i main` (squash prototype commits); keep the Linear ID in the final commit.
- Merge with `--no-ff` into `main` and push.
- Keep the bugfix commit separate from feature commits.


## Screenshots and Evidence
- Add screenshots of:
  - Running service terminal output.
  - A successful summary displayed in the app.
  - The UI error state when the service is down.
- Upload to the corresponding Linear issue and reference commit SHAs.


## Deliverables Checklist
- Feature 1 (Element) branch merged: service code + tests; commits include [VERITAS-25].
- Feature 2 (Interaction) branch merged: Next.js route + minimal UI; commits include [VERITAS-22].
- Bugfix branch merged with separate commit including [VERITAS-44].
- Updated architecture diagram with ticket IDs committed under `docs/architecture/`.
- Linear tickets populated with background, description, dependencies, test plan, prompts, and screenshots.


## Appendix: Gemini example (for reference)
The following is a minimal snippet showing how to call Gemini (adapted for clarity). Prefer the service implementation shown above for production logic.

```python
# Dependencies: pip install google-genai
import os
from google import genai
from google.genai import types

def generate_summary(text: str) -> str:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=text)])
    ]
    res = client.models.generate_content(
        model="gemini-flash-latest",
        contents=contents,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=8000)
        ),
    )
    return (res.text or "").strip()
```


