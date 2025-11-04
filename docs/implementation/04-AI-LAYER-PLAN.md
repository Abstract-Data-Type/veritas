# AI Layer Implementation Plan: VeritasNews

**Author:** Yann Calvo Lopez (AI Lead)
**Date:** November 3, 2025
**Status:** FINAL

## 1. Overview & Goals

The AI Layer is a core component of VeritasNews, responsible for two primary functions:
1.  **Unbiased Summarization:** Generating concise, neutral summaries of news articles to give users a quick overview of the facts.
2.  **Political Bias Analysis:** Providing raw data inputs to a deterministic scoring system that assesses articles for potential bias.

This plan outlines the scaffolding needed to create a basic, end-to-end bias analysis pipeline.

## 2. Methodology: Bias Assessment Framework

Our new approach prioritizes simplicity and a clear separation of concerns. The LLM's role is to act as a focused data provider, answering specific questions. Our service's code will then be responsible for the final interpretation and scoring.

**Critical Design Principle: Extensibility First**

The scaffolding must be built with future enhancements in mind. We will create a flexible framework that can easily accommodate:
- Any number of parallel LLM calls (not hardcoded to 4)
- Different scoring strategies (averages, weighted formulas, etc.)
- Additional dimensions or questions without major refactoring

### 2.1. Extensible Multi-Query Protocol

-   **Process:** For each article, we will make N separate, parallel calls to the LLM—one for each bias dimension/question. Currently, N = 4, but the framework must support any number of questions.
-   **Framework Design:** The system will be built around a configurable list of questions, where each question defines:
    -   The dimension name (e.g., "partisan_bias")
    -   The prompt to send to the LLM
    -   The expected response format (currently a single number 1-7)
-   **Rationale:** This approach isolates each analytical task, allowing for highly specific and simple prompts. It avoids the complexity of large, multi-part prompts and reduces the risk of the model's reasoning on one dimension influencing another.
-   **Initial Model Selection:** We will start with **Gemini 2.5 flash** for its good balance of reasoning, latency, and cost.

### 2.2. LLM as Data Provider

-   The LLM's sole responsibility is to return a single number (from 1 to 7) for each question.
-   All LLM calls will be made with a low **`temperature` (e.g., `0.1`)** to promote factual and deterministic responses.

### 2.3. Pluggable Scoring Function

-   The framework will include a **scoring function** that takes the raw numerical outputs from all LLM calls and produces the final scores.
-   **Initial Implementation:** The scoring function will be a simple pass-through that returns the raw numbers as-is. This function will be designed as a pluggable component that can be easily swapped or extended.
-   **Future Extensibility:** The scoring function can be extended to:
    -   Calculate weighted averages across multiple models
    -   Apply normalization or scaling
    -   Implement complex formulas that combine dimensions
    -   Add confidence scores or other metadata
-   **Design Pattern:** The scoring function will accept a dictionary/map of dimension names to raw scores and return a dictionary of dimension names to final scores. This allows for easy swapping of scoring strategies without changing the rest of the pipeline.

### 2.4. Bias Dimensions & Questions

These remain the core of our analysis. Each question corresponds to one API call.

| Dimension | Question | Scoring Scale |
| :--- | :--- | :--- |
| **Partisan Bias** | On a scale of 1-7, does this article's language, framing, and sourcing favor a political party or ideology? | `1` = Strongly favors the Left<br>`4` = Neutral / Balanced<br>`7` = Strongly favors the Right |
| **Affective Bias (Tone)** | On a scale of 1-7, how emotionally charged or inflammatory is the language used in the article? | `1` = Strictly neutral, objective tone<br>`4` = Moderately emotive language<br>`7` = Highly emotional, loaded language |
| **Framing Bias** | On a scale of 1-7, does the article frame issues in a way that consistently benefits one perspective? | `1` = Consistently frames for the Left<br>`4` = Uses neutral framing<br>`7` = Consistently frames for the Right |
| **Sourcing Bias** | On a scale of 1-7, how diverse are the sources and viewpoints quoted or referenced in the article? | `1` = Sources are from one-sided or uniform perspectives<br>`4` = Some diversity in sources<br>`7` = Wide diversity of sources and viewpoints |

## 3. System Architecture & Integration Workflow

### 3.1. High-Level Workflow

The AI service operates as a microservice that the main backend application calls. Here is the complete workflow:

1.  **Backend Retrieves Article:** The main backend application (managed by Jackson Webster) retrieves an unprocessed article from the database.
2.  **Backend Calls AI Service:** The backend makes two separate HTTP POST requests to the AI service:
    -   One to `/summarize` to get the article summary
    -   One to `/rate-bias` to get the bias scores
3.  **AI Service Processes:** The AI service receives the article text, calls the LLM (Gemini) as needed, and returns the results.
4.  **Backend Stores Results:** The backend receives both responses and stores the summary and bias scores back into the database alongside the original article.

### 3.2. API Endpoints

The AI service exposes two endpoints that the backend will call:

#### `POST /summarize` (Existing)
-   **Request:**
  ```json
  {
    "article_text": "The full text of the article to be summarized..."
  }
  ```
-   **Response:**
  ```json
  {
    "summary": "A concise, unbiased summary of the article..."
  }
  ```
-   **Status:** Already implemented and working.

#### `POST /rate-bias` (New)
-   **Request:**
  ```json
  {
    "article_text": "The full text of the article to be analyzed..."
  }
  ```
-   **Response:**
  ```json
  {
    "scores": {
      "partisan_bias": 4.0,
      "affective_bias": 3.0,
      "framing_bias": 5.0,
      "sourcing_bias": 6.0
    },
    "ai_model": "gemini-2.5-flash"
  }
  ```
-   **Note:** Field renamed from `model_used` to `ai_model` to avoid Pydantic protected namespace warning.
-   **Status:** Implemented in VERITAS-AI-01.

### 3.3. Integration Points for Backend Team (Jackson)

**Location of AI Service:** The AI service runs as a FastAPI application located in `services/summarization/`. It can be started independently and exposes HTTP endpoints.

**What the Backend Needs to Implement:**

1.  **Database Schema Updates:**
    -   Add a `summary` column (or table field) to store the article summary (TEXT/VARCHAR).
    -   Add columns to store the four bias scores:
        -   `partisan_bias` (FLOAT, range 1-7)
        -   `affective_bias` (FLOAT, range 1-7)
        -   `framing_bias` (FLOAT, range 1-7)
        -   `sourcing_bias` (FLOAT, range 1-7)
    -   Optionally, add a `model_used` field to track which AI model generated the scores.

2.  **HTTP Client Function:**
    -   Create a function (e.g., `process_article_with_ai(article_id: int)`) that:
        -   Retrieves the article from the database (by ID or other identifier).
        -   Extracts the article text (from whichever field contains it).
        -   Makes an HTTP POST request to `http://<ai-service-url>/summarize` with the article text.
        -   Makes an HTTP POST request to `http://<ai-service-url>/rate-bias` with the article text.
        -   Handles errors appropriately (e.g., if the AI service is down, log the error and optionally retry).
        -   Stores the returned `summary` and the four bias scores back into the database for that article.
    -   **Recommended:** Use an HTTP client library like `httpx` or `requests` for Python.

3.  **Service Configuration:**
    -   Ensure the backend knows the URL/port of the AI service (e.g., via environment variable `AI_SERVICE_URL`).

**What the AI Service Provides:**
-   Two RESTful endpoints that accept article text and return structured JSON responses.
-   Error handling: Returns appropriate HTTP status codes (400 for bad input, 502 for LLM failures).
-   The service is stateless and idempotent: calling it multiple times with the same article text will produce the same results (within the variance of the LLM).

## 3.4. Technical Reference: Gemini API Usage

This section provides the technical documentation for calling Gemini models using the `google-genai` SDK.

### Installation

```bash
pip install google-genai
```

### Basic Usage Pattern

```python
import os
from google import genai
from google.genai import types

# Initialize the client
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
)

# Define the model
model = "gemini-flash-latest"  # or "gemini-2.5-flash" for our use case

# Prepare the content
contents = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_text(text="""INSERT_INPUT_HERE"""),
        ],
    ),
]

# Configure generation parameters
generate_content_config = types.GenerateContentConfig(
    temperature=0.1,  # Low temperature for factual, deterministic responses
    max_output_tokens=150,  # Adjust based on needs
)

# For synchronous calls (recommended for our API endpoints):
result = client.models.generate_content(
    model=model,
    contents=contents,
    config=generate_content_config,
)

response_text = result.text

# For streaming calls (if needed):
for chunk in client.models.generate_content_stream(
    model=model,
    contents=contents,
    config=generate_content_config,
):
    print(chunk.text, end="")
```

### Key Configuration Options

-   **`temperature`**: Controls randomness (0.0-1.0). Use `0.1` for factual, consistent responses.
-   **`max_output_tokens`**: Limits response length. For bias scores (single numbers), use a small value (e.g., 10-20). For summaries, use a larger value (e.g., 150).
-   **`thinking_config`**: Optional advanced reasoning configuration (not needed for our initial implementation).
-   **`tools`**: Optional tool calling configuration (not needed for our initial implementation).

### Implementation Notes for AI Service

1.  **API Key Management:** Store `GEMINI_API_KEY` in environment variables (already configured in existing `/summarize` endpoint).
2.  **Error Handling:** Wrap calls in try-except blocks to handle API failures gracefully.
3.  **Synchronous vs Streaming:** Use synchronous `generate_content()` for our API endpoints (simpler, sufficient for our use case).
4.  **Model Selection:** Start with `gemini-flash-latest` or `gemini-2.5-flash` as specified in the plan.

## 3.5. Architectural Considerations for Implementation

To ensure the AI service is robust, scalable, and maintainable, the following architectural principles must be followed during implementation.

1.  **Externalize Configuration:** The question registry (defining dimensions, prompts, etc.) must not be hardcoded in Python. It should be loaded from an external file (e.g., `prompts.yaml`) at startup. This allows for changes to prompts and the addition of new dimensions without requiring a code deployment.

2.  **Ensure Endpoint Atomicity:** The `/rate-bias` endpoint must be atomic. If any of the N parallel calls to the Gemini API fail, the entire endpoint must fail and return an appropriate error code (e.g., HTTP 502 Bad Gateway). Partial results must not be returned.

3.  **Implement Defensive Response Parsing:** Never trust the format of the LLM's response. The implementation must include a robust parsing and validation layer that:
    -   Handles cases where the LLM returns text instead of a number.
    -   Validates that the returned number is within the expected range (e.g., 1-7).
    -   Sanitizes the output to a clean integer/float before it's used.

4.  **Leverage Asynchronous Execution:** To ensure performance, the N parallel calls to the Gemini API must be executed concurrently, not sequentially. The implementation should use Python's `asyncio` library and an asynchronous HTTP client.

5.  **Service Naming:** The service's directory should be refactored from `services/summarization/` to `services/ai_service/` to accurately reflect its expanded responsibilities. This will be a separate follow-up ticket.

## 4. Implementation Plan & Tickets

This section outlines all the tickets needed to complete the AI layer implementation. The first ticket (VERITAS-AI-01) is the foundational scaffolding that must be completed today. The remaining tickets represent future enhancements.

### Phase 1: Foundational Scaffolding (Today)

**VERITAS-AI-01: Implement Foundational Bias Scoring Scaffolding**
-   **Goal:** Create a working end-to-end pipeline that takes an article, makes N parallel LLM calls to get raw scores for each bias dimension, and returns the compiled scores. **Critical:** Build this as an extensible framework, not hardcoded logic.
-   **Estimate:** 6 hours
-   **Tasks:**
    -   Create the `/rate-bias` endpoint in the AI (FastAPI) service.
    -   Set up the Gemini SDK and API key handling.
    -   **Build Extensible Framework:**
        -   Create a configurable question registry loaded from an external file (e.g., `prompts.yaml`) that defines each bias dimension and its prompt.
        -   Implement a generic parallel LLM caller using `asyncio` to handle any number of questions concurrently.
        -   Design the scoring function as a pluggable component that accepts a dictionary of raw scores and returns final scores.
        -   Implement the initial scoring function as a simple pass-through.
    -   Develop four simple, focused prompts (one for each bias question).
    -   **Implement Robust Error Handling:**
        -   The `/rate-bias` endpoint must be atomic. If any LLM call fails, the entire request must fail with an HTTP 502 error.
        -   Implement a defensive parsing and validation layer for all LLM responses to handle unexpected formats and ensure scores are within the valid 1-7 range.
-   **Dependencies:** None (foundational ticket)
-   **Note:** Jackson will implement the backend integration separately. The AI service must be ready to receive HTTP requests from the backend.

**Test Plan:**
-   **Unit Tests:**
    -   Test the parsing of the `prompts.yaml` configuration file.
    -   Test the pluggable scoring function with mock dictionary inputs to ensure it returns the expected dictionary output.
    -   Test the defensive parsing of LLM responses (e.g., provide "five", 7.2, "N/A" and ensure it handles them gracefully).
-   **Integration Tests (using `pytest` and `httpx`):**
    -   Mock the Gemini API client.
    -   Test the `/rate-bias` endpoint with a valid article text and assert it returns a 200 OK status with the correct JSON structure.
    -   Test the endpoint with an empty `article_text` payload and assert it returns a 400 Bad Request.
    -   Test the endpoint with a mocked Gemini API failure on one of the four calls and assert it returns a 502 Bad Gateway.
    -   Test that for a valid request, the mocked Gemini client is called exactly N times (where N is the number of questions in the config).

---

### Phase 2: Prompt Engineering & Testing

**VERITAS-AI-02: Refine and Test Bias Dimension Prompts**
-   **Goal:** Systematically test and iterate on the four dimension-specific prompts to ensure they consistently return valid numbers and are resilient to varied article styles.
-   **Estimate:** 5 hours
-   **Tasks:**
    -   Create a benchmark suite of 20-30 articles representing a wide range of political leanings, topics, and writing styles.
    -   Run each article through the `/rate-bias` endpoint and log the results.
    -   Analyze outputs for failures (e.g., non-numeric responses, out-of-range values) and inconsistencies.
    -   Iteratively refine prompt wording to improve reliability and accuracy.
-   **Test Plan:**
    -   **Manual Validation:** Create a spreadsheet to manually track the LLM's output for each article in the benchmark suite across multiple runs.
    -   **Success Criteria:** Define a success metric, e.g., "the prompts must return a valid integer between 1-7 in >98% of test cases."
    -   **Edge Case Testing:** The benchmark suite must include articles that are very short, very long, highly satirical, or written in non-standard English to test the prompts' robustness.
-   **Dependencies:** VERITAS-AI-01

### Phase 3: Advanced Scoring

**VERITAS-AI-03: Develop a Nuanced Deterministic Scoring Formula**
-   **Goal:** Evolve the scoring from a simple pass-through to a more sophisticated, weighted formula that better represents overall bias.
-   **Estimate:** 4 hours
-   **Tasks:**
    -   Research established methodologies for weighting media bias factors.
    -   Design and implement a new formula within the AI service code.
    -   Ensure the formula is easily adjustable for future tuning.
-   **Test Plan:**
    -   **Unit Tests:** Create a comprehensive suite of unit tests for the new scoring function.
    -   **Test Cases:** Test with various input vectors: all neutral scores (e.g., `[4,4,4,4]`), all high scores, all low scores, and a mix of scores.
    -   **Assertion:** Assert that the output scores match the expected values calculated by hand.
    -   **Edge Cases:** Test how the formula handles missing or invalid inputs (though the validation layer should prevent this, the function should still be robust).
-   **Dependencies:** VERITAS-AI-02 (the formula needs reliable inputs)

### Phase 4: Testing & Quality Assurance

**VERITAS-AI-04: Write Comprehensive Tests for the AI Service**
-   **Goal:** Ensure the AI service is reliable and maintainable by implementing the comprehensive test plans defined in other tickets.
-   **Estimate:** 5 hours
-   **Tasks:**
    -   Implement the unit tests for the scoring formula as defined in `VERITAS-AI-03`.
    -   Implement the integration tests for the `/rate-bias` and `/summarize` endpoints as defined in `VERITAS-AI-01` and `VERITAS-AI-05`.
    -   Set up mocking for the Gemini API to ensure tests are fast, predictable, and do not incur costs.
    -   Integrate the tests into a CI/CD pipeline if available.
-   **Test Plan:** The task of this ticket *is* to implement the test plans from other tickets. Success is measured by the test suite passing reliably.
-   **Dependencies:** VERITAS-AI-01, VERITAS-AI-02, VERITAS-AI-03, VERITAS-AI-05

### Phase 5: Enhanced Features

**VERITAS-AI-05: Add Justifications to Bias API Response**
-   **Goal:** Provide transparency by including brief justifications for each bias score, explaining why the article received that rating.
-   **Estimate:** 4 hours
-   **Tasks:**
    -   Update the four bias prompts to request a one-sentence justification in addition to the numerical score (must return structured JSON).
    -   Modify the LLM response parsing logic to extract both score and justification.
    -   Update the `/rate-bias` API response model to include justification fields.
    -   Coordinate with frontend and backend teams to ensure new data can be stored and displayed.
-   **Test Plan:**
    -   **Unit Tests:** Write unit tests for the updated response parsing logic to ensure it correctly handles the new JSON structure.
    -   **Integration Tests:** Update the integration tests for `/rate-bias`. The mock Gemini API should return the new `{"score": x, "justification": "..."}` structure.
    -   **Contract Testing:** Assert that the API response body correctly includes the new `justification` fields.
-   **Dependencies:** VERITAS-AI-01

**VERITAS-AI-06: Implement Advanced LLM Protocol (Scorer-Reviewer)**
-   **Goal:** Enhance analysis quality by introducing a two-step "scorer-reviewer" protocol where a second LLM call critiques and refines the initial score.
-   **Estimate:** 6 hours
-   **Tasks:**
    -   Update core logic to make sequential calls for each dimension (scorer first, then reviewer).
    -   Create a new "reviewer" prompt that receives the article, initial score, and critiques it.
    -   Update the pipeline to return the reviewer's final score.
    -   Note: This increases LLM calls from 4 to 8 per article (cost and performance considerations).
-   **Test Plan:**
    -   **Unit Tests:** Test the orchestration logic that handles the two-step call sequence.
    -   **Integration Tests:** Update the integration tests for `/rate-bias`. The mock Gemini API should be called twice per dimension.
    -   **Assertion:** Assert that the final score returned by the endpoint is the one from the "reviewer" mock call, not the "scorer."
    -   **Failure Testing:** Test that if either the scorer or reviewer call fails, the entire request fails with a 502 error.
-   **Dependencies:** VERITAS-AI-01

**VERITAS-AI-07: Refactor AI Service Naming and Structure**
-   **Goal:** Improve clarity and maintainability of the codebase by renaming the service directory to reflect its expanded role.
-   **Estimate:** 1 hour
-   **Tasks:**
    -   Rename the `services/summarization/` directory to `services/ai_service/`.
    -   Update any import paths, CI/CD pipeline configurations, or documentation that may reference the old path.
    -   Ensure all tests pass after the refactor.
-   **Test Plan:**
    -   **Regression Testing:** The primary test is to run the entire existing test suite (`VERITAS-AI-04`) after the refactor and ensure all tests pass.
    -   **Manual End-to-End Test:** Manually start the refactored service and make a `curl` request to both endpoints to ensure they are still functional.
-   **Dependencies:** VERITAS-AI-04

## 5. Backend Integration Notes (For Jackson)

As outlined in Section 3.3, the backend team needs to implement:

1.  **Database schema updates** to store summaries and bias scores.
2.  **HTTP client function** to call both AI service endpoints and store results.
3.  **Service configuration** to know the AI service URL.

The AI service will be ready to receive requests once VERITAS-AI-01 is complete. The endpoints are stateless and can be called independently by the backend.

## 6. Tickets for Linear (Copy-Paste Ready)

The following tickets are formatted for direct copy-paste into Linear. Each ticket includes all necessary details for the assignment requirements (estimates, dependencies, clear descriptions).

### **Ticket 1: Foundational Scaffolding (Today's Priority)**

**Title:** `VERITAS-AI-01: Implement Foundational Bias Scoring Scaffolding`

**Description:**
This is the foundational ticket for the AI layer. The goal is to create a working end-to-end pipeline that serves as the scaffolding for all future AI features. **Critical:** This must be built as an extensible framework, not hardcoded logic. The framework must support any number of questions and different scoring strategies.

**Estimate:** 6 hours

**Implementation Details:**
- Create the `/rate-bias` endpoint within the existing FastAPI service located at `services/summarization/`.
- Set up the Gemini SDK and handle API key configuration securely (build on existing `/summarize` endpoint setup).
- **Build Extensible Framework Architecture:**
  - Create a configurable question registry (list/dict) that defines each bias dimension with its prompt. Currently 4 questions, but architecture must support adding/removing questions easily.
  - Implement a generic parallel LLM caller that can handle any number of questions (not hardcoded to 4).
  - Design the scoring function as a pluggable component that accepts a dictionary of dimension names → raw scores and returns dimension names → final scores.
  - Implement the initial scoring function as a simple pass-through (returns raw scores as-is).
- Develop four simple, focused prompts (one for each bias question) that instruct the Gemini model to return only a single number between 1 and 7.
- Ensure proper error handling for LLM API failures (return appropriate HTTP status codes).
- The framework should be designed so that adding new dimensions, changing prompts, or swapping scoring strategies requires minimal code changes.

**Dependencies:** None (foundational ticket)

**Note:** Jackson will implement the backend integration separately. The AI service must be ready to receive HTTP requests from the backend.

**Test Plan:**
-   **Unit Tests:**
    -   Test the parsing of the `prompts.yaml` configuration file.
    -   Test the pluggable scoring function with mock dictionary inputs to ensure it returns the expected dictionary output.
    -   Test the defensive parsing of LLM responses (e.g., provide "five", 7.2, "N/A" and ensure it handles them gracefully).
-   **Integration Tests (using `pytest` and `httpx`):**
    -   Mock the Gemini API client.
    -   Test the `/rate-bias` endpoint with a valid article text and assert it returns a 200 OK status with the correct JSON structure.
    -   Test the endpoint with an empty `article_text` payload and assert it returns a 400 Bad Request.
    -   Test the endpoint with a mocked Gemini API failure on one of the four calls and assert it returns a 502 Bad Gateway.
    -   Test that for a valid request, the mocked Gemini client is called exactly N times (where N is the number of questions in the config).

---

### **Ticket 2: Prompt Engineering & Testing**

**Title:** `VERITAS-AI-02: Refine and Test Bias Dimension Prompts`

**Description:**
The quality of our bias analysis is highly dependent on the quality of our prompts. This ticket is for systematically testing and refining the four dimension-specific prompts to ensure we get consistent, reliable, and accurate numerical outputs from the LLM.

**Implementation Details:**
- Create a benchmark suite of 20-30 articles from across the political spectrum, representing different topics and writing styles.
- For each of the four prompts, run them against the benchmark suite and analyze the results.
- Tweak the wording of the prompts to improve clarity and reduce ambiguity.
- Ensure the prompts reliably produce a single integer between 1-7 and handle edge cases (e.g., very short or opinion-focused articles) gracefully.

**Dependencies:** Is Blocked By: VERITAS-AI-01

**Estimate:** 5 hours

---

### **Ticket 3: Advanced Scoring Formula**

**Title:** `VERITAS-AI-03: Develop a Nuanced Deterministic Scoring Formula`

**Description:**
Currently, our scoring is a simple pass-through of the raw data from the LLM. This ticket is to evolve that into a more sophisticated and meaningful scoring model that is calculated deterministically in our code.

**Implementation Details:**
- Research and define a weighted scoring model. For example, we might decide that "Partisan Bias" and "Framing Bias" are more indicative of overall bias than "Affective Bias (Tone)".
- Implement this new formula in the `/rate-bias` endpoint logic. The code will take the four raw numbers from the LLM as input and compute a final set of scores.
- The API response structure will likely remain the same, but the values will be the result of this new calculation.

**Dependencies:** Is Blocked By: VERITAS-AI-02 (the formula needs reliable inputs first)

**Estimate:** 4 hours

---

### **Ticket 4: Comprehensive Testing**

**Title:** `VERITAS-AI-04: Write Comprehensive Tests for the AI Service`

**Description:**
To ensure the AI service is reliable and maintainable, we need a robust test suite. This ticket covers the creation of both unit and integration tests for our core endpoints.

**Implementation Details:**
- Write unit tests for the deterministic scoring formula to verify its correctness with various inputs.
- Write integration tests for the `/rate-bias` and `/summarize` endpoints.
- In the integration tests, the calls to the Gemini SDK must be mocked. This ensures our tests are fast, predictable, and do not incur API costs.
- Test edge cases: empty text, very long articles, API failures.

**Dependencies:** Is Blocked By: VERITAS-AI-01, VERITAS-AI-02

**Estimate:** 5 hours

---

### **Ticket 5: Add Justifications**

**Title:** `VERITAS-AI-05: Add Justifications to Bias API Response`

**Description:**
To build user trust and provide transparency, we should show *why* an article received a certain score. This ticket involves updating our prompts and API to include brief, LLM-generated justifications for each bias score.

**Implementation Details:**
- Modify each of the four bias-rating prompts to request a brief, one-sentence justification in addition to the numerical score. The prompt must demand a structured JSON output (e.g., `{"score": 5, "justification": "..."}`).
- Update the `/rate-bias` endpoint response to include these justifications.
- This will require close collaboration with the backend and frontend teams to ensure the new data can be stored and displayed correctly in the UI.

**Dependencies:** Is Blocked By: VERITAS-AI-01

**Estimate:** 4 hours

---

### **Ticket 6: Advanced Protocol (Future Enhancement)**

**Title:** `VERITAS-AI-06: Implement Advanced LLM Protocol (Scorer-Reviewer)`

**Description:**
This ticket is for a future enhancement to improve the robustness of our bias analysis. We will implement a two-step "scorer-reviewer" protocol, where a second LLM call is made to critique and refine the initial score.

**Implementation Details:**
- Update the core logic for the `/rate-bias` endpoint to be sequential for each dimension.
- The first call (scorer) will produce a number as it does now.
- A new, second prompt (reviewer) will be created. It will receive the article, the first score, and be asked to critically evaluate it and provide a final score.
- This will increase the LLM call count from 4 to 8 per article, so performance and cost implications should be noted.

**Dependencies:** Is Blocked By: VERITAS-AI-01

**Estimate:** 6 hours

---

### **Ticket 7: Refactor AI Service Naming and Structure**

**Title:** `VERITAS-AI-07: Refactor AI Service Naming and Structure`

**Description:**
To improve the clarity and maintainability of the codebase, the service directory should be renamed to reflect its expanded role of handling all AI-related tasks, not just summarization.

**Implementation Details:**
-   Rename the `services/summarization/` directory to `services/ai_service/`.
-   Update any import paths, CI/CD pipeline configurations, or documentation that may reference the old path.
-   Ensure all tests pass after the refactor.

**Dependencies:** Is Blocked By: VERITAS-AI-01

**Estimate:** 1 hour

---

## 8. Workflow & Submission Guidelines (for HW8)

This section outlines the specific process for implementing and submitting the work for this assignment.

### Git Workflow
-   **Branching:** All work must be done in a dedicated feature branch named `github_username-hw8`. For pairs, use `username1-username2-hw8`. Example: `yannCLopez-hw8`.
-   **Commits:** All commit messages must include the string "HW8" and the Linear ticket ID. Example: `git commit -m "HW8 VERITAS-AI-01: Implement async caller for bias rating"`
-   **Merging:** You should merge your feature branch into `main` after your work is complete and tested.

### Linear & Bug Reporting
-   **Labels:** All tickets related to this assignment must have the `HW8` label in Linear.
-   **Bug Reports:** It is acceptable to ship features with non-showstopper bugs, provided they are ticketed. Bug reports must include:
    1.  The correct (desired) behavior.
    2.  Steps to reproduce the bug.
    3.  The actual (wrong) behavior.
    4.  A link to the feature the bug affects.

## 9. Summary

This plan provides a comprehensive roadmap for implementing the AI Layer of VeritasNews. The implementation is structured in phases:

- **Phase 1 (Today):** Build the foundational scaffolding that enables the entire AI layer to function end-to-end. **Critical:** This scaffolding must be built as an extensible framework that supports any number of questions and pluggable scoring strategies.
- **Phases 2-5:** Enhance and refine the system with improved prompts, sophisticated scoring, comprehensive testing, and advanced features.

**Key Architectural Principles:**
- **Extensibility First:** The framework supports N parallel LLM calls (not hardcoded) and a pluggable scoring function that can be easily swapped or extended.
- **Separation of Concerns:** LLM provides raw data; our code handles interpretation and scoring.
- **Future-Proof Design:** Adding new dimensions, changing prompts, or implementing new scoring formulas requires minimal refactoring.

The plan includes:
- Clear methodology for bias assessment using an extensible multi-query protocol
- Detailed integration points for the backend team
- Six well-defined tickets with estimates and dependencies
- Architecture that supports future enhancements without major rewrites

All tickets are formatted for direct use in Linear and include the necessary details required for the assignment (estimates, dependencies, clear task descriptions).

