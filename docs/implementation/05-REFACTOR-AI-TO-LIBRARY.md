# Refactor AI Microservice to Library Module

Ticket: VERITAS-REFACTOR-01  
Type: Refactoring  
Priority: Medium  
Status: Not Started

---

## Goal

Refactor the AI summarization and bias analysis functionality from a separate FastAPI microservice (`services/summarization/`) into a library module (`src/ai/`) that can be directly imported and called by the main backend application. This eliminates unnecessary HTTP overhead, simplifies deployment, and improves maintainability while preserving all existing functionality.

Critical: Maintain 100% backward compatibility in terms of functionality - all existing features must work identically, just with a simpler architecture.

---

## Estimate

Estimated: 3 hours  
Actual: TBD

---

## Background & Rationale

Currently, the AI functionality (summarization and bias analysis) exists as a separate FastAPI microservice that the main backend calls via HTTP. This creates unnecessary complexity:

- Operational overhead: Two services to start, monitor, and deploy
- Performance overhead: HTTP network calls (even on localhost) add latency
- Code complexity: HTTP client code, error handling, timeouts, connection management
- Testing complexity: Need to mock HTTP calls instead of functions
- Deployment complexity: Separate Dockerfile, separate process management

Since only ONE backend application uses this functionality, a microservice architecture provides no benefits. Converting to a library will:
- Simplify the codebase
- Improve performance (no network overhead)
- Make testing easier (direct function calls)
- Reduce operational complexity (single service)

---

## Tasks

### 1. Create New Library Module Structure
- Create `src/ai/` directory with `__init__.py`
- Set up module exports for public API (`summarize()`, `rate_bias()`)

### 2. Migrate Core AI Logic
- Move `services/summarization/bias_analysis.py` → `src/ai/bias_analysis.py`
- Move `services/summarization/config.py` → `src/ai/config.py`
- Move `services/summarization/scoring.py` → `src/ai/scoring.py`
- Move `services/summarization/prompts.yaml` → `src/ai/prompts.yaml`
- Extract `summarize_with_gemini()` from `services/summarization/main.py` → `src/ai/summarization.py`
- Convert `rate_bias()` endpoint handler → `rate_bias()` function in `src/ai/bias_analysis.py`
- Update all imports and path references (especially `config.py` loading `prompts.yaml`)

### 3. Update Backend Integration Points
- Update `src/api/routes_bias_ratings.py`:
  - Replace HTTP calls in `/analyze` endpoint with direct `rate_bias()` function call
  - Replace HTTP calls in `/summarize` endpoint with direct `summarize_with_gemini()` function call
  - Remove `httpx` imports and `SUMMARIZATION_SERVICE_URL` references
  - Update error handling to use Python exceptions instead of HTTP status codes
  
- Update `src/worker/pipeline.py`:
  - Replace `_get_article_summary()` HTTP call with direct `summarize_with_gemini()` function call
  - Remove `SUMMARIZATION_SERVICE_URL` reference
  - Update error handling

### 4. Migrate and Update Tests (TDD Approach)
- Migrate tests from `services/summarization/tests/`:
  - `test_rate_bias.py` → `tests/test_ai_bias_analysis.py` (update imports)
  - `test_summarize.py` → `tests/test_ai_summarization.py` (update imports)
  - `test_e2e_rate_bias.py` → `tests/test_ai_e2e.py` (update for library context)
  - `test_edge_cases.py` → `tests/test_ai_edge_cases.py` (update imports)
  
- Update existing backend tests:
  - `tests/test_summarization.py` - Update mocks to mock functions instead of HTTP calls
  - `tests/test_bias_ratings.py` - Update mocks for `/analyze` endpoint
  - `tests/test_integration_bugs.py` - Remove `SUMMARIZATION_SERVICE_URL` related tests
  - `tests/test_validation_bug.py` - Update validation consistency tests
  
- Delete obsolete tests:
  - `tests/test_url_bug.py` - No longer relevant (no URL construction)

### 5. Update Dependencies
- Add `google-genai==0.3.0` to main `requirements.txt` (if not already present)
- Add `pyyaml==6.0.2` to main `requirements.txt` (if not already present)
- Verify all dependencies from `services/summarization/requirements.txt` are covered
- Remove FastAPI/uvicorn from microservice context (keep if used elsewhere)

### 6. Remove Microservice Infrastructure
- Delete `services/summarization/` directory (after migration verified)
- Delete `start_summarization.sh` startup script
- Delete `services/summarization/Dockerfile`
- Remove `SUMMARIZATION_SERVICE_URL` environment variable references from:
  - Code files
  - Documentation
  - README
  - Test fixtures

### 7. Update Documentation
- Update `README.md` - Remove "Start the Summarization Microservice" section
- Update `docs/guides/EXAMINER.md` - Update architecture decisions section
- Update `docs/guides/QUICK_START.md` - Simplify setup instructions
- Update `docs/testing/TESTING.md` - Remove microservice setup instructions
- Update `docs/implementation/04-AI-LAYER-PLAN.md` - Note architecture change
- Update all other docs referencing microservice architecture

---

## Dependencies

Prerequisites:
- Existing AI functionality must be working (summarization + bias analysis)
- All existing tests must pass before refactoring

Blocks:
- None (this is a refactoring ticket, not a feature addition)

---

## Test Plan

### Unit Tests (Function-Level)

- Test `src/ai/config.py`:
  - Test loading `prompts.yaml` configuration file
  - Test caching mechanism (`get_prompts_config()` returns same object)
  - Test error handling for missing/invalid YAML file
  - Test validation of dimension structure (name, prompt fields)

- Test `src/ai/scoring.py`:
  - Test `score_bias()` pass-through implementation with mock dictionary inputs
  - Verify it returns a copy (not same object reference)
  - Verify output dictionary structure matches input

- Test `src/ai/bias_analysis.py`:
  - Test `parse_llm_score()` defensive parsing:
    - Valid integers ("5" → 5.0)
    - Valid floats ("5.2" → 5.2)
    - Written numbers ("five" → 5.0)
    - Clamping (7.5 → 7.0, 0.5 → 1.0)
    - Invalid responses ("N/A", "", "invalid") → ValueError
  - Test `call_llm_for_dimension()` with mocked Gemini client
  - Test `rate_bias_parallel()` with all successful calls
  - Test `rate_bias_parallel()` atomic failure (one call fails → entire operation fails)

- Test `src/ai/summarization.py`:
  - Test `summarize_with_gemini()` with mocked Gemini client
  - Test error handling for missing API key
  - Test error handling for API failures

### Integration Tests (Module-Level)

- Test `src/api/routes_bias_ratings.py` `/analyze` endpoint:
  - Mock `src.ai.bias_analysis.rate_bias_parallel()` function
  - Test successful analysis with valid article_id
  - Test article not found (404)
  - Test article with no text content (422)
  - Test existing rating returned (no duplicate analysis)
  - Test function failure → 502 error response
  - Verify database storage of bias rating

- Test `src/api/routes_bias_ratings.py` `/summarize` endpoint:
  - Mock `src.ai.summarization.summarize_with_gemini()` function
  - Test successful summarization
  - Test empty article_text (422)
  - Test function failure → 502 error response

- Test `src/worker/pipeline.py` `_get_article_summary()`:
  - Mock `src.ai.summarization.summarize_with_gemini()` function
  - Test successful summary generation
  - Test function failure → returns None (graceful degradation)
  - Test short article text → returns None (skipped)

### End-to-End Tests (System-Level)

- Test full bias analysis flow:
  - Create article in database
  - Call `/bias_ratings/analyze` endpoint
  - Verify bias rating stored in database with correct scores
  - Verify all 4 dimensions present in scores dictionary

- Test full summarization flow:
  - Call `/bias_ratings/summarize` endpoint
  - Verify summary returned in response
  - Verify summary is non-empty string

### Regression Tests

- Run all existing tests to ensure nothing broke:
  - `tests/test_bias_ratings.py`
  - `tests/test_summarization.py`
  - `tests/test_worker_*.py`
  - All other integration tests

---

## Acceptance Criteria

- [ ] All AI functionality works identically to before (no behavior changes)
- [ ] All existing tests pass (100% pass rate)
- [ ] No HTTP calls to `SUMMARIZATION_SERVICE_URL` remain in codebase
- [ ] All tests use function mocks instead of HTTP mocks
- [ ] `services/summarization/` directory removed
- [ ] Documentation updated to reflect library architecture
- [ ] Single service deployment (no separate microservice)
- [ ] Performance improvement verified (no network overhead)

---

## Notes

- TDD Approach: Update tests first, then refactor code. This ensures we maintain functionality throughout the refactor.
- Backward Compatibility: The public API (endpoints) remains the same - only internal implementation changes.
- No Feature Changes: This is purely a refactoring ticket - no new features, no behavior changes.
- Gradual Migration: Can be done incrementally - migrate one endpoint at a time, verify tests pass, then continue.

---

## Risk Assessment

Risk Level: Low

Mitigation:
- Comprehensive test suite ensures functionality preserved
- Incremental migration approach (one endpoint at a time)
- All existing tests must pass before considering complete
- Can rollback easily (git revert) if issues arise

Potential Issues:
- Import path changes might break if not updated everywhere
- Async function signatures need to match exactly
- Error handling might need adjustment (exceptions vs HTTP status)

