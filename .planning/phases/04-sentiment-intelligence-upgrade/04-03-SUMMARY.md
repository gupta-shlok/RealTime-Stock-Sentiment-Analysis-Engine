---
phase: 04-sentiment-intelligence-upgrade
plan: 03
subsystem: backend/api-endpoints
tags: [fastapi, sentiment-trends, sector-sentiment, stock-narrative, qwen, ema, tdd, pytest]

# Dependency graph
requires:
  - phase: 04-02
    provides: sentiment_scores.json written by sentiment_scoring_task; _load_scores_file/_load_narratives_file/_write_json_atomic helpers; finbert_score() tuple; aggregate_daily_score()

provides:
  - GET /sentiment-trends endpoint with EMA smoothing (SENT-03)
  - GET /sector-sentiment endpoint with stock_count >= 3 filter (SENT-04)
  - GET /stock-narrative/{ticker} endpoint with 1-hour cache freshness (SENT-05)
  - build_narrative_prompt() and get_qwen_narrative() helper functions
  - _get_ticker_headlines() pulling top 8 headlines from news_cache for a ticker
  - qwen_worker() extended to handle job type 'narrative' writing to narratives.json
  - WINDOW_TO_SPAN = {"7d": 5, "30d": 20} constant
  - 10 green endpoint tests in test_endpoints.py

affects:
  - 05 (UI Overhaul — frontend sentiment chart, heatmap, and narrative components consume all three endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - EMA via pandas.Series.ewm(span=N).mean() on ISO date-keyed dict from sentiment_scores.json
    - Sector aggregation: latest score per constituent, stock_count >= 3 gate excludes small sectors
    - Narrative caching: 1-hour TTL checked via (datetime.now(utc) - generated_at).total_seconds() < 3600
    - qwen_worker job type branching: job.get("type", "analyze") dispatches to narrative vs analyze paths
    - TestClient + patch("main._load_scores_file") pattern for hermetic endpoint tests without filesystem I/O
    - app.dependency_overrides[require_api_key] to bypass API key auth in TestClient tests

key-files:
  created: []
  modified:
    - backend/main.py
    - backend/tests/test_endpoints.py

key-decisions:
  - "WINDOW_TO_SPAN maps 7d->span=5 and 30d->span=20 — invalid window returns HTTP 400 (not 200 empty)"
  - "sector-sentiment stock_count counts tickers WITH data, not total sector tickers — Real Estate (2 tickers) always excluded"
  - "stock-narrative endpoint checks narrative age via UTC-aware datetime comparison; corrupt/missing tzinfo falls through to enqueue"
  - "qwen_worker branches on job.get('type', 'analyze') defaulting to original analyze-custom behavior — zero regression risk"

requirements-completed: [SENT-03, SENT-04, SENT-05]

# Metrics
duration: 7min
completed: 2026-03-28
---

# Phase 4 Plan 03: Sentiment Endpoints — /sentiment-trends, /sector-sentiment, /stock-narrative Summary

**Three API endpoints added to expose Plan 02 scoring infrastructure; qwen_worker extended for narrative jobs; all 10 endpoint stub tests activated and passing; full Phase 4 suite: 24 tests green**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-28T13:23:00Z
- **Completed:** 2026-03-28T13:30:00Z
- **Tasks:** 2
- **Files modified:** 2 (backend/main.py, backend/tests/test_endpoints.py)

## Accomplishments

- Added `build_narrative_prompt()` — formats top 8 headlines with FinBERT scores into a Qwen prompt asking for a 2-3 sentence sentiment narrative citing specific headlines
- Added `_get_ticker_headlines()` — pulls articles from `news_cache["news"]` for a ticker, sorts by publishTime descending, scores each title via `finbert_score()`, returns top 8
- Added `get_qwen_narrative()` — synchronous Qwen generation called via `asyncio.to_thread()` from qwen_worker; returns narrative string
- Extended `qwen_worker()` with `job_type = job.get("type", "analyze")` branching: "narrative" path calls `get_qwen_narrative()`, writes result to `NARRATIVES_FILE` via `_write_json_atomic()`, stores in `qwen_job_results[job_id]`; default "analyze" path is unchanged
- Added `WINDOW_TO_SPAN = {"7d": 5, "30d": 20}` constant
- Added `GET /sentiment-trends` — loads `sentiment_scores.json`, validates window parameter (returns HTTP 400 for invalid), computes `pd.Series.ewm(span=N).mean()` on ticker's date-keyed scores
- Added `GET /sector-sentiment` — iterates `SECTOR_TICKERS`, takes latest date score per constituent, applies `stock_count >= 3` gate (Real Estate: 2 tickers excluded)
- Added `GET /stock-narrative/{ticker}` — checks `narratives.json` freshness (< 3600 seconds), returns `status:"complete"` on cache hit or enqueues Qwen job and returns `status:"pending"` with UUID job_id
- Activated all 10 endpoint stub tests in `test_endpoints.py`: 4 sentiment-trends, 3 sector-sentiment, 3 stock-narrative

## Task Commits

1. **Task 1: Add /sentiment-trends, /sector-sentiment, /stock-narrative endpoints and extend qwen_worker** — `495698d` (feat)
2. **Task 2: Activate test_endpoints.py — implement all endpoint stub tests** — `0619382` (feat)

## Files Created/Modified

- `backend/main.py` — Added build_narrative_prompt(), _get_ticker_headlines(), get_qwen_narrative(), extended qwen_worker(), added WINDOW_TO_SPAN, GET /sentiment-trends, GET /sector-sentiment, GET /stock-narrative/{ticker}
- `backend/tests/test_endpoints.py` — Replaced 10 pytest.skip stubs with full test implementations; module-scoped TestClient with model mocks and dependency_overrides

## Decisions Made

- `WINDOW_TO_SPAN` maps "7d"->span=5 and "30d"->span=20. Invalid window raises HTTP 400 — not a 200 with empty data, because an invalid window is a client error, not a missing-data scenario.
- `stock_count` in `/sector-sentiment` counts tickers that have at least one date entry in `sentiment_scores.json`, not the total tickers in `SECTOR_TICKERS`. Real Estate (EQIX, SPG = 2 tickers) is always excluded.
- `/stock-narrative/{ticker}` does timezone-aware datetime comparison: if `generated_at` lacks tzinfo, it is explicitly set to UTC before comparison to avoid TypeError on Python 3.11+.
- `qwen_worker` job type defaults to "analyze" — existing `/analyze-custom` callers pass `{"job_id": ..., "text": ...}` without a "type" key; the default preserves full backward compatibility.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Real Estate ticker names in test_sector_sentiment_exclusion**
- **Found during:** Task 2 — writing tests; noticed plan used "AMT" and "PLD" but tickers.py Real Estate sector has "EQIX" and "SPG"
- **Issue:** Plan's test used `"AMT": {...}, "PLD": {...}` but SECTOR_TICKERS["Real Estate"] = ['EQIX', 'SPG']. Using wrong tickers would not trigger the exclusion path correctly.
- **Fix:** Changed test data to use correct Real Estate tickers: `"EQIX": {"2026-03-28": 0.10}, "SPG": {"2026-03-28": -0.05}`
- **Files modified:** `backend/tests/test_endpoints.py`
- **Commit:** `0619382`

## Known Stubs

None. All three endpoints read from real `sentiment_scores.json` written by `sentiment_scoring_task()` at runtime. The endpoints return empty/pending responses when data is absent, which is correct behavior — not a stub.

## Issues Encountered

- RuntimeWarnings about unawaited coroutines at teardown (`qwen_worker` and `sentiment_scoring_task`) — harmless artifact of `patch("main.asyncio.create_task")` preventing background task startup. Tests pass cleanly; warnings are expected in test context.

## User Setup Required

None. All three endpoints are available immediately on server startup. Narratives require Qwen model to be loaded (handled in lifespan).

## Next Phase Readiness

- Phase 5 (UI Overhaul) can now build against all three endpoints
- `/sentiment-trends?ticker=AAPL&window=7d` — ready for chart overlay component
- `/sector-sentiment` — ready for heatmap sector grouping
- `/stock-narrative/AAPL` — ready for narrative panel with polling on job_id

## Self-Check: PASSED

- FOUND: backend/main.py — contains `@app.get("/sentiment-trends")`, `@app.get("/sector-sentiment")`, `@app.get("/stock-narrative/{ticker}")`
- FOUND: backend/main.py — contains `WINDOW_TO_SPAN = {"7d": 5, "30d": 20}`
- FOUND: backend/main.py — contains `def build_narrative_prompt(`
- FOUND: backend/main.py — contains `def get_qwen_narrative(`
- FOUND: backend/main.py — contains `job_type = job.get("type", "analyze")`
- FOUND: backend/main.py — contains `"narrative"` inside qwen_worker handling block
- FOUND: backend/main.py — contains `_write_json_atomic(NARRATIVES_FILE`
- FOUND: backend/tests/test_endpoints.py — 10 tests, 0 pytest.skip
- VERIFIED: `pytest backend/tests/ -v` — 24 passed, 0 failed, 0 skipped
- VERIFIED: `git log` shows commits `495698d` and `0619382`

---

*Phase: 04-sentiment-intelligence-upgrade*
*Completed: 2026-03-28*
