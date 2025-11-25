# Multi-Dimensional Bias Scoring Implementation

## Goal

Expand the bias rating system from a single `bias_score` field to a multi-dimensional scoring model with four separate dimensions: partisan bias, affective bias, framing bias, and sourcing bias. This provides more nuanced analysis, enables dimension-specific filtering and visualization, and differentiates our platform from existing single-score bias checkers.

Critical: Maintain 100% backward compatibility - existing API endpoints must continue to work, and we must handle existing null scores gracefully.

---

## Estimate

Estimated: 2-3 hours

Actual: TBD

---

## Background & Rationale

Currently, the AI bias analysis returns 4-dimensional scores (partisan, affective, framing, sourcing) but we only store a single `bias_score` field (currently null in the database). This creates several problems:

- Lost Information: Rich multi-dimensional analysis is reduced to a single number (or lost entirely)
- Limited Functionality: Cannot filter/sort by specific bias dimensions
- Missed Opportunity: Single-score bias checkers are commodity - multi-dimensional scoring is a real differentiator
- Poor UX: Cannot show users nuanced breakdown of bias types

The AI layer already generates 4 scores - we're just not storing them properly. By adding dedicated columns for each dimension, we:

- Preserve all AI analysis output
- Enable dimension-specific queries (e.g., "show articles with high partisan bias but low affective bias")
- Support richer visualizations (radar charts, dimension comparisons)
- Provide more actionable insights to users
- Maintain type safety and structured data

The team has agreed this is the right approach, with the requirement to add utility functions for computing overall bias scores.

---

## Tasks

### 1. Update Database Schema

- Add 4 new columns to `BiasRating` model (`src/models/sqlalchemy_models.py`):
  - `partisan_bias: Mapped[Optional[float]]` - measures left/right political lean
  - `affective_bias: Mapped[Optional[float]]` - measures emotional language intensity
  - `framing_bias: Mapped[Optional[float]]` - measures narrative framing and perspective
  - `sourcing_bias: Mapped[Optional[float]]` - measures source diversity and viewpoint balance
  - All fields should be `Float`, nullable=True
  - All fields should accept values 1.0-7.0 (matching AI scoring scale)

- Keep existing `bias_score` field for backward compatibility
  - Will be computed as average of 4 dimensions (or left as-is for legacy data)

### 2. Create Database Migration

- Option A: Simple SQLite Migration (Recommended for development):
  - Create migration script `src/db/migrations/add_bias_dimensions.py`
  - Use SQLAlchemy to add columns: `ALTER TABLE bias_ratings ADD COLUMN ...`
  - Test on development database first
  
- Option B: Recreate Development Database (If no critical data):
  - Delete `veritas_news.db`
  - Run `init_db()` to recreate with new schema
  - Faster but loses existing data

- Backfill Strategy:
  - Existing rows with null dimension scores can stay null
  - New analyses will populate all 4 dimensions
  - Optional: Re-analyze existing articles to backfill (future ticket)

### 3. Update AI Integration Layer

- Update `src/ai/bias_analysis.py`:
  - Verify `rate_bias_parallel()` already returns all 4 dimension scores
  - Ensure return format is: `{"partisan_bias": float, "affective_bias": float, "framing_bias": float, "sourcing_bias": float}`
  - Update type hints if needed

- Update `src/api/routes_bias_ratings.py`:
  - Modify `/analyze` endpoint to extract scores from `rate_bias()` response
  - Map dimension names from AI response to database columns:
    - `scores["partisan_bias"]` → `partisan_bias`
    - `scores["affective_bias"]` → `affective_bias`
    - `scores["framing_bias"]` → `framing_bias`
    - `scores["sourcing_bias"]` → `sourcing_bias`
  - Update `BiasRating` object creation to include all 4 fields
  - Ensure response includes all 4 dimensions in JSON output
  - Update response model/schema if defined

### 4. Create Utility Functions (Per Vineet's Request)

- Create `src/models/bias_rating.py` utility module:
  ```python
  def get_overall_bias_score(bias_rating: BiasRating) -> Optional[float]:
      """Compute average of 4 dimensions as overall bias score."""
      
  def get_all_dimension_scores(bias_rating: BiasRating) -> Dict[str, Optional[float]]:
      """Return dictionary of all 4 dimension scores."""
      
  def get_dimension_score(bias_rating: BiasRating, dimension: str) -> Optional[float]:
      """Get individual dimension score by name."""
  ```

- Edge cases to handle:
  - Null scores (legacy data)
  - Partial scores (some dimensions null)
  - Invalid dimension names

### 5. Update API Response Models

- Update response schema (if using Pydantic models):
  - Add `partisan_bias`, `affective_bias`, `framing_bias`, `sourcing_bias` fields
  - Keep `bias_score` for backward compatibility (compute from dimensions)
  - Ensure all fields are Optional[float]

- Update API documentation:
  - Document each dimension's meaning
  - Document scoring scale (1.0 = most left/least biased, 7.0 = most right/most biased)
  - Add examples of multi-dimensional scores

### 6. Update Tests

- Update `tests/test_bias_ratings.py`:
  - Test creating BiasRating with all 4 dimensions
  - Test storing and retrieving dimension scores
  - Test null handling (legacy data)
  - Test `/analyze` endpoint returns all 4 dimensions

- Update `tests/test_ai_bias_analysis.py`:
  - Verify `rate_bias_parallel()` returns all 4 dimensions
  - Test dimension score parsing and validation

- Create `tests/test_bias_utils.py`:
  - Test `get_overall_bias_score()` with:
    - All 4 dimensions present (should average)
    - Some dimensions null (should average non-null values)
    - All dimensions null (should return None)
  - Test `get_all_dimension_scores()` dictionary output
  - Test `get_dimension_score()` with valid/invalid dimension names

### 7. Update Documentation

- Update `README.md`:
  - Add section explaining multi-dimensional bias scoring
  - Document each dimension with examples

- Update `docs/guides/QUICK_START.md`:
  - Update bias analysis examples to show all 4 dimensions
  - Add examples of querying by dimension

- Update API documentation:
  - Update `/bias_ratings/analyze` endpoint docs
  - Add dimension descriptions and scoring scale

---

## Dependencies

Prerequisites:
- AI bias analysis must already be returning 4-dimensional scores (currently implemented)
- Database must be using SQLAlchemy ORM (currently implemented)
- Existing tests must pass before starting

Blocks:
- None (self-contained feature addition)

Blocked By:
- None

---

## Test Plan

### Unit Tests (Model-Level)

- Test `BiasRating` model (`tests/test_init_db.py` or new test):
  - Create BiasRating with all 4 dimension scores
  - Verify all fields save correctly to database
  - Verify all fields retrieve correctly from database
  - Test null values for each dimension
  - Test valid score range (1.0-7.0)
  - Test invalid scores (negative, > 7.0, non-numeric)

- Test utility functions (`tests/test_bias_utils.py`):
  - `get_overall_bias_score()`:
    - All dimensions present: (3.0, 4.0, 5.0, 6.0) → 4.5
    - Some null: (3.0, None, 5.0, None) → 4.0
    - All null: (None, None, None, None) → None
    - Edge: (1.0, 7.0, 1.0, 7.0) → 4.0
  - `get_all_dimension_scores()`:
    - Returns dict with all 4 keys
    - Handles null values correctly
    - Returns copy (not reference to internal state)
  - `get_dimension_score()`:
    - Valid dimension names return correct values
    - Invalid dimension names raise ValueError
    - Null scores return None

### Integration Tests (API-Level)

- Test `/bias_ratings/analyze` endpoint (`tests/test_bias_ratings.py`):
  - Create article with text content
  - Call `/analyze` endpoint
  - Verify response includes all 4 dimension scores:
    - `partisan_bias` present and in range 1.0-7.0
    - `affective_bias` present and in range 1.0-7.0
    - `framing_bias` present and in range 1.0-7.0
    - `sourcing_bias` present and in range 1.0-7.0
  - Verify `bias_score` computed as average
  - Query database to confirm all 4 dimensions stored
  - Verify backward compatibility (existing fields still present)

- Test GET `/bias_ratings/{article_id}` endpoint:
  - Retrieve bias rating with dimension scores
  - Verify all 4 dimensions in response
  - Test with legacy data (null dimensions) - should handle gracefully

### Database Migration Tests

- Test migration script:
  - Run migration on test database
  - Verify all 4 new columns added
  - Verify existing columns unaffected
  - Verify existing data preserved (null values for new columns)
  - Verify new columns accept null values
  - Verify new columns accept float values in range 1.0-7.0

- Test backward compatibility:
  - Load existing BiasRating records (with null dimensions)
  - Verify no errors when accessing dimension fields
  - Verify utility functions handle null dimensions

### End-to-End Tests

- Full bias analysis flow:
  1. Create article in database via API
  2. Call `/bias_ratings/analyze` endpoint
  3. Verify response contains all 4 dimension scores
  4. Query database directly to confirm storage
  5. Retrieve via GET endpoint, verify all dimensions present
  6. Test utility functions on stored rating

- Regression test: Run all existing tests to ensure nothing broke

---

## Acceptance Criteria

- [ ] Database schema updated with 4 new columns (`partisan_bias`, `affective_bias`, `framing_bias`, `sourcing_bias`)
- [ ] Migration script created and tested on development database
- [ ] All new columns nullable, accept float values 1.0-7.0
- [ ] `/bias_ratings/analyze` endpoint stores all 4 dimension scores
- [ ] `/bias_ratings/analyze` endpoint returns all 4 dimension scores in response
- [ ] Utility functions implemented and tested:
  - [ ] `get_overall_bias_score()` - computes average
  - [ ] `get_all_dimension_scores()` - returns dict of all scores
  - [ ] `get_dimension_score()` - gets individual dimension
- [ ] Existing `bias_score` field maintained for backward compatibility
- [ ] All unit tests passing (100% pass rate)
- [ ] All integration tests passing
- [ ] Documentation updated with dimension descriptions
- [ ] Backward compatibility verified (handles null/legacy data)

---

## Notes

### Dimension Definitions

Based on AI bias analysis implementation (`src/ai/prompts.yaml`):

- **Partisan Bias** (1-7): Direct political alignment
  - 1 = Strongly favors/criticizes the Left (explicit support for left-leaning parties/ideologies)
  - 4 = Neutral / No explicit partisan alignment
  - 7 = Strongly favors/criticizes the Right (explicit support for right-leaning parties/ideologies)

- **Affective Bias** (1-7): Emotional language intensity
  - 1 = Strictly neutral, objective tone
  - 4 = Moderately emotive language
  - 7 = Highly emotional, loaded language

- **Framing Bias** (1-7): Narrative framing and perspective
  - 1 = Framing strongly favors left-leaning perspectives (emphasizes left concerns/angles)
  - 4 = Uses neutral, balanced framing with multiple perspectives
  - 7 = Framing strongly favors right-leaning perspectives (emphasizes right concerns/angles)

- **Sourcing Bias** (1-7): Source diversity and viewpoint balance
  - 1 = Sources are from one-sided or uniform perspectives
  - 4 = Some diversity in sources
  - 7 = Wide diversity of sources and viewpoints

### Implementation Notes

- Migration Strategy: For development, simplest approach is ALTER TABLE. For production, consider more robust migration tool (Alembic).
- Backward Compatibility: Keep `bias_score` field populated (as average) so old code expecting single score continues to work.
- Future Enhancement: Add computed column for overall score, or database trigger to auto-populate.
- Visualization Ready: Multi-dimensional data enables radar charts, dimension comparison views, filtering by specific bias types.


## Risk Assessment

Risk Level: Low-Medium

Mitigation:
- Database migration is additive only (no data loss risk)
- Existing `bias_score` field preserved (backward compatibility)
- All new fields nullable (no breaking changes)
- Comprehensive test suite ensures functionality
- Can rollback migration if issues arise

Potential Issues:
- Migration failure: Test on development database first, backup production before migration
- AI not returning 4 scores: Verify AI layer output format before implementing storage
- Null handling: Ensure all utility functions gracefully handle null/partial scores
- Performance: 4 columns vs 1 has negligible impact, but test query performance
- API breaking change: Ensure response schema remains backward compatible (add fields, don't remove)

Rollback Plan:
- If migration fails: Restore database backup
- If API breaks: Revert code changes (git revert)
- If tests fail: Fix implementation before deploying
- Migration script should be reversible (DROP COLUMN if needed)

---

## Future Enhancements (Out of Scope)

- [ ] Backfill existing null dimension scores by re-analyzing articles
- [ ] Add database constraints (CHECK score >= 1.0 AND score <= 7.0)
- [ ] Create radar chart visualization for dimensions
- [ ] Add dimension-specific filtering in frontend
- [ ] Compute dimension trends over time
- [ ] Add weighted average option (not all dimensions equal)
- [ ] Add confidence scores for each dimension

---

## References

- Team Slack discussion: 10/11/2025, 21:45-22:19
- AI bias analysis implementation: `src/ai/bias_analysis.py`
- Database models: `src/models/sqlalchemy_models.py`
- Bias ratings API: `src/api/routes_bias_ratings.py`
