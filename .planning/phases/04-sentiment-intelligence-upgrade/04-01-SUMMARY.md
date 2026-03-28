---
phase: 04-sentiment-intelligence-upgrade
plan: 01
subsystem: testing
tags: [pytest, pytest-asyncio, fastapi, finbert, unittest.mock]

# Dependency graph
requires:
  - phase: 03-data-pipeline-expansion
    provides: tickers.py with SECTOR_TICKERS used in test_sector_sentiment_exclusion

provides:
  - pytest 9.0.2 + pytest-asyncio 1.3.0 test infrastructure
  - backend/pytest.ini with asyncio_mode = auto
  - backend/tests/conftest.py with mock_finbert_model, mock_finbert_tokenizer, sample_scores_data, sample_narratives_data fixtures
  - 24 stub tests covering SENT-01 through SENT-05 (all skipped pending implementation plans)

affects:
  - 04-02 (FinBERT scoring implementation — tests in test_finbert.py and test_aggregation.py become live)
  - 04-03 (endpoint implementation — tests in test_endpoints.py become live)

# Tech tracking
tech-stack:
  added:
    - pytest==9.0.2
    - pytest-asyncio==1.3.0
  patterns:
    - Stub-first TDD: write all tests as pytest.skip() stubs before any implementation; pytest exits 0 from day 0
    - Session-scoped fixtures for expensive mock setup (mock_finbert_model, mock_finbert_tokenizer)
    - asyncio_mode = auto in pytest.ini eliminates per-test event loop boilerplate

key-files:
  created:
    - backend/pytest.ini
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_finbert.py
    - backend/tests/test_aggregation.py
    - backend/tests/test_endpoints.py
  modified:
    - backend/requirements.txt

key-decisions:
  - "All 24 stub tests use pytest.skip() (not xfail) so the suite is always green and any accidental removal of a skip causes an immediate failure"
  - "Fixtures are session-scoped to avoid re-creating torch tensors for every test function"
  - "Real Estate exclusion test documents EQIX as the only real-estate ticker found in tickers.py (AMT is not present), confirming stock_count < 3 gate"

patterns-established:
  - "Pattern 1: conftest.py holds all model mocks at session scope — no test file imports torch directly for mock setup"
  - "Pattern 2: stub docstrings carry the exact acceptance criteria and expected values so implementers can copy them directly into assertions"

requirements-completed: [SENT-01, SENT-02, SENT-03, SENT-04, SENT-05]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 4 Plan 01: Pytest Infrastructure & Stub Tests Summary

**pytest 9.0.2 test harness with 24 stub tests covering SENT-01 through SENT-05, all skipped and exiting 0 before any implementation begins**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T12:44:56Z
- **Completed:** 2026-03-28T12:47:06Z
- **Tasks:** 2
- **Files modified:** 7 (1 modified, 6 created)

## Accomplishments

- Installed pytest 9.0.2 and pytest-asyncio 1.3.0; created pytest.ini with `asyncio_mode = auto`
- Created conftest.py with 4 session-scoped fixtures (mock model, mock tokenizer, sample scores data, sample narratives data) using torch mocks — no real FinBERT or Qwen loaded
- Wrote 24 stub tests across 3 files mapping exactly to SENT-01 (8 tests), SENT-02 (6 tests), and SENT-03/04/05 (10 tests); `pytest tests/ -x -q` exits 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Install pytest dependencies and create pytest.ini** - `0b3893f` (chore)
2. **Task 2: Create conftest.py and stub test files** - `6b19303` (test)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified

- `backend/pytest.ini` - pytest config: asyncio_mode=auto, testpaths=tests
- `backend/requirements.txt` - Added pytest==9.0.2 and pytest-asyncio==1.3.0 under # Testing section
- `backend/tests/__init__.py` - Package marker (empty)
- `backend/tests/conftest.py` - Session-scoped fixtures: mock_finbert_model, mock_finbert_tokenizer, sample_scores_data, sample_narratives_data
- `backend/tests/test_finbert.py` - 8 SENT-01 stub tests: label_order, score_direction_positive/negative, score_range, confidence_is_max_softmax, finbert_score_returns_tuple, neutral_not_dominant, low_confidence_appears_in_news
- `backend/tests/test_aggregation.py` - 6 SENT-02 stub tests: weighted_mean_basic/equal_confidence, all_below_threshold, partial_threshold_filter, empty_articles_returns_none, scoring_cycle_groups_and_aggregates
- `backend/tests/test_endpoints.py` - 10 SENT-03/04/05 stub tests: sentiment_trends_7d/30d/invalid/unknown, sector_sentiment_inclusion/exclusion/shape, narrative_cache_hit/pending/unknown_ticker_enqueues

## Decisions Made

- Used `pytest.skip()` (not `pytest.mark.xfail`) for all stubs so the suite stays green and accidental skip removal causes immediate failure rather than a silent pass
- Fixtures are session-scoped to avoid rebuilding torch tensors per test function (performance)
- Real Estate exclusion stub documents that only EQIX appears as Real Estate in tickers.py (AMT is not present) — confirmed stock_count will be 1 (well below the >= 3 gate)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Test infrastructure complete; Plans 02 and 03 can immediately replace `pytest.skip()` stubs with real assertions
- Plan 02 (FinBERT scoring) targets test_finbert.py + test_aggregation.py — 14 tests will go live
- Plan 03 (endpoints) targets test_endpoints.py — 10 tests will go live
- No blockers. `pytest tests/ -v` exits 0 with all 24 skipped.

---

*Phase: 04-sentiment-intelligence-upgrade*
*Completed: 2026-03-28*
