# Bug VERITAS-44: Backend Accepts Empty Summary as Valid Response

**Type:** Bug  
**Priority:** High  
**Component:** Backend API - Summarization Integration  
**Affects:** VERITAS-43

## Description

The backend's `/bias_ratings/summarize` endpoint accepts empty or whitespace-only summaries as valid successful responses. This is a **silent failure** that returns HTTP 200 OK with an empty summary field, which could confuse users and downstream systems.

## Root Cause

**Location:** `src/api/routes_bias_ratings.py` line 198

```python
if response.status_code == 200:
    data = response.json()
    return {"summary": data.get("summary", "")}  # BUG: Returns empty string as success
```

The code uses `.get("summary", "")` which returns an empty string if:
1. The 'summary' field is missing from the JSON response
2. The 'summary' field contains an empty string
3. The 'summary' field contains only whitespace

## Impact

- **Silent failures**: Users receive "successful" responses with no actual content
- **Poor user experience**: No error message explains why the summary is empty
- **Downstream system confusion**: Other services can't distinguish between success and failure
- **Data quality issues**: Empty summaries could be stored as valid data

## Steps to Reproduce

1. Mock summarization service to return `{"wrong_field": "data"}` with status 200
2. Call `/bias_ratings/summarize` endpoint
3. Observe: Returns 200 OK with `{"summary": ""}` instead of error

## Expected Behavior

Should return HTTP 502 Bad Gateway with error message when summary is empty or missing.

## Test Evidence

See: `tests/test_empty_summary_bug.py`
- `test_empty_summary_returned_as_success()` - PASSES (confirms bug)
- `test_empty_summary_string_returned_as_success()` - PASSES (confirms bug)
- `test_whitespace_only_summary_returned_as_success()` - PASSES (confirms bug)

