# Bug VERITAS-45: Improper 4xx Status Code Handling from Summarization Service

**Type:** Bug  
**Priority:** Medium  
**Component:** Backend API - Summarization Integration  
**Affects:** VERITAS-43

## Description

The backend's `/bias_ratings/summarize` endpoint doesn't properly handle 4xx status codes (400, 422, etc.) returned by the summarization microservice. All 4xx errors are incorrectly converted to 500 Internal Server Error instead of being properly forwarded to the client.

## Root Cause

**Location:** `src/api/routes_bias_ratings.py` lines 196-210

```python
if response.status_code == 200:
    # Handle success
elif response.status_code >= 500:
    # Handle server errors → 502
else:
    # BUG: ALL other codes (including 400, 422) → 500
    logger.warning(f"Unexpected response from summarization service: {response.status_code}")
    raise HTTPException(
        status_code=500,
        detail="Failed to generate summary"
    )
```

## Impact

- **Incorrect HTTP semantics**: Client errors (4xx) are reported as server errors (5xx)
- **Debugging difficulty**: The true error type is hidden from API consumers
- **Violates REST API best practices**: HTTP status codes lose their semantic meaning
- **Confusion for API consumers**: Can't distinguish between client-side and server-side errors

## Example Scenarios

- Service returns 400 (Bad Request) → Backend incorrectly returns 500
- Service returns 422 (Validation Error) → Backend incorrectly returns 500
- Service returns 429 (Rate Limit) → Backend incorrectly returns 500

## Steps to Reproduce

1. Mock summarization service to return status 400
2. Call `/bias_ratings/summarize` endpoint
3. Observe: Backend returns 500 instead of forwarding 400

## Expected Behavior

- 400-499 from service → Forward as 400 with error details
- 500-599 from service → Return 502 Bad Gateway

## Test Evidence

See: `tests/test_status_code_bug.py`
- `test_400_status_code_handling_bug()` - Shows 400 → 500 conversion
- `test_422_status_code_handling_bug()` - Shows 422 → 500 conversion

