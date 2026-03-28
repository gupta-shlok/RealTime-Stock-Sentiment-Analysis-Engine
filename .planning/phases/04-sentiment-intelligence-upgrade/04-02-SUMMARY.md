---
phase: 04-sentiment-intelligence-upgrade
plan: 02
subsystem: backend/ml-scoring
tags: [finbert, sentiment-scoring, aggregation, background-task, tdd, pytest]

# Dependency graph
requires:
  - phase: 04-01
    provides: pytest infrastructure, stub tests in test_finbert.py and test_aggregation.py

provides:
  - finbert_score() returning (score, confidence) tuple via AutoModelForSequenceClassification
  - aggregate_daily_score() with confidence-weighted mean and threshold filter (SENT-02)
  - sentiment_scoring_task() background asyncio task writing sentiment_scores.json every 5 min
  - _run_scoring_cycle() reading news_cache and persisting scores with 35-day pruning
  - DATA_DIR, SCORES_FILE, NARRATIVES_FILE path constants
  - FINBERT_MIN_CONFIDENCE=0.55 config setting
  - 14 green tests (8 finbert + 6 aggregation)

affects:
  - 04-03 (endpoint implementation — /sentiment-trends, /sector-sentiment, /stock-narrative all read from sentiment_scores.json produced by this plan)
  - 05 (UI endpoints — frontend sentiment chart data flows from scoring task output)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - AutoModelForSequenceClassification forward pass replaces pipeline() shortcut for full softmax access
    - Confidence-weighted mean: sum(score*conf) / sum(conf) for articles passing threshold
    - Atomic JSON write via tempfile + os.replace() for safe concurrent access
    - Background asyncio task pattern: asyncio.to_thread() wraps synchronous scoring loop

key-files:
  created:
    - backend/.env.example
  modified:
    - backend/config.py
    - backend/main.py
    - backend/tests/test_finbert.py
    - backend/tests/test_aggregation.py

key-decisions:
  - "finbert_score() returns (score, confidence) tuple not float — all callers must unpack; score=P(pos)-P(neg) in [-1,1], confidence=max(softmax)"
  - "aggregate_daily_score() returns None (not 0.0) when no articles pass threshold — callers must check for None to skip days with insufficient confidence"
  - "SCORES_FILE written atomically via os.replace() to prevent partial reads by concurrent endpoint calls (D-10)"
  - "Auto-fixed: test_weighted_mean_basic had wrong expected value in plan (-0.45) using confidence=0.3 < 0.55 threshold; fixed to confidence=0.6 and correct expected -0.24"

requirements-completed: [SENT-01, SENT-02]

# Metrics
duration: 8min
completed: 2026-03-28
---

# Phase 4 Plan 02: FinBERT Full-Probability Scoring and Aggregation Summary

**FinBERT pipeline() replaced with AutoModelForSequenceClassification full-probability scoring; confidence-weighted daily aggregation with threshold filter; background 5-minute scoring task writing sentiment_scores.json; 14 unit tests green**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-28T12:48:21Z
- **Completed:** 2026-03-28T12:55:13Z
- **Tasks:** 2
- **Files modified:** 4 (2 modified + 1 created + 1 modified)

## Accomplishments

- Replaced `pipeline("sentiment-analysis")` shortcut with `AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")` — now has direct access to full softmax probability distribution
- `finbert_score()` now returns `(score, confidence)` tuple where `score = P(positive) - P(negative)` and `confidence = max(softmax(logits))`
- `analyze_sentiment_ensemble()` unpacks tuple correctly (`score, _ = finbert_score(text)`) — /news endpoint unaffected
- `qwen_worker()` updated to unpack tuple (`fb_val, _ = finbert_score(text)`)
- Added `aggregate_daily_score()` with confidence-weighted mean that excludes articles where `confidence < FINBERT_MIN_CONFIDENCE` (default 0.55)
- Added `_run_scoring_cycle()` that reads `news_cache["news"]`, groups by (ticker, date), scores each article title, aggregates daily scores, prunes entries older than 35 days, and writes `sentiment_scores.json` atomically
- Added `sentiment_scoring_task()` async background loop: 10s startup delay, then runs scoring cycle every 300s
- Added `FINBERT_MIN_CONFIDENCE = 0.55` to `config.py` Settings class
- Lifespan updated: loads `finbert_model` + `finbert_tokenizer` via `AutoModelForSequenceClassification`, sets `app.state.finbert_model` and `app.state.finbert_tokenizer`, starts `sentiment_scoring_task` background worker
- Activated 14 stub tests: 8 finbert + 6 aggregation — all pass green

## Task Commits

1. **Task 1: Add FINBERT_MIN_CONFIDENCE to config and upgrade FinBERT loading in lifespan** — `5969836` (feat)
2. **Task 2: Replace finbert_score(), add aggregate_daily_score(), scoring task, activate tests** — `cbcb612` (feat)

## Files Created/Modified

- `backend/config.py` — Added `finbert_min_confidence: float = 0.55` field to Settings class
- `backend/main.py` — Replaced pipeline import/usage with AutoModelForSequenceClassification; added _finbert_infer(), finbert_score() tuple, analyze_sentiment_ensemble(), aggregate_daily_score(), persistence helpers, _run_scoring_cycle(), sentiment_scoring_task(); updated lifespan and qwen_worker
- `backend/tests/test_finbert.py` — Activated 8 tests (was all pytest.skip stubs)
- `backend/tests/test_aggregation.py` — Activated 6 tests (was all pytest.skip stubs)
- `backend/.env.example` — Created with FINBERT_MIN_CONFIDENCE entry (and other settings)

## Decisions Made

- `finbert_score()` returns a tuple: callers MUST unpack. This is a breaking change from the old `float` return. All 3 callers were updated in this plan.
- `aggregate_daily_score()` returns `None` (not 0.0) when no articles pass threshold — distinguishes "no data" from "truly neutral" (important for Plan 03 trend endpoints)
- `_run_scoring_cycle()` is synchronous and called via `asyncio.to_thread()` to avoid blocking the event loop during FinBERT inference over potentially many articles
- `_write_json_atomic()` uses `tempfile.mkstemp` + `os.replace()` — atomic on both Windows and Linux (D-10)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed wrong expected value in test_weighted_mean_basic**
- **Found during:** Task 2 — first test run
- **Issue:** Plan specified `articles = [{"score": -0.8, "confidence": 0.9}, {"score": 0.6, "confidence": 0.3}]` with expected `-0.45`. But `confidence=0.3 < 0.55` (threshold), so the second article is filtered. With only the first article, result is `-0.8`, not `-0.45`. The plan's formula comment ignored the threshold filter.
- **Fix:** Changed second article confidence from `0.3` to `0.6` (above threshold). New expected value: `(-0.8*0.9 + 0.6*0.6) / (0.9 + 0.6) = -0.24`. Test still validates the core behavior: high-confidence bearish outweighs lower-confidence bullish.
- **Files modified:** `backend/tests/test_aggregation.py`
- **Commit:** `cbcb612`

## Known Stubs

None. All functions introduced in this plan are fully implemented. `sentiment_scoring_task()` writes real data at runtime — no placeholder logic.

## Issues Encountered

- `@lru_cache` on `get_settings()` required tests to patch `main.get_settings` (not `config.get_settings`) for the mock to take effect in `aggregate_daily_score()`. Tests correctly patch at `main.get_settings`.

## User Setup Required

None. `backend/.env.example` documents `FINBERT_MIN_CONFIDENCE=0.55` for reference.

## Next Phase Readiness

- `sentiment_scores.json` will be written by `sentiment_scoring_task()` once the server starts and `news_cache["news"]` is populated
- Plan 03 (endpoints) can now implement `/sentiment-trends`, `/sector-sentiment`, `/stock-narrative` — all read from `SCORES_FILE` and `NARRATIVES_FILE`
- `test_endpoints.py` has 10 stub tests ready to be activated in Plan 03

## Self-Check: PASSED

- FOUND: backend/config.py — contains `finbert_min_confidence: float = 0.55`
- FOUND: backend/main.py — contains `AutoModelForSequenceClassification`, `finbert_score() -> tuple`, `aggregate_daily_score()`, `sentiment_scoring_task()`, `_run_scoring_cycle()`
- FOUND: backend/tests/test_finbert.py — 8 tests active, 0 pytest.skip
- FOUND: backend/tests/test_aggregation.py — 6 tests active, 0 pytest.skip
- FOUND: .planning/phases/04-sentiment-intelligence-upgrade/04-02-SUMMARY.md
- VERIFIED: `git log` shows commits `5969836` and `cbcb612`
- VERIFIED: `pytest tests/test_finbert.py tests/test_aggregation.py -v` — 14 passed, 0 failed

---

*Phase: 04-sentiment-intelligence-upgrade*
*Completed: 2026-03-28*
