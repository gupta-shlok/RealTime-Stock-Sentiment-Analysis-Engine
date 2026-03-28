---
phase: 04-sentiment-intelligence-upgrade
verified: 2026-03-28T14:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 4: Sentiment Intelligence Upgrade — Verification Report

**Phase Goal:** Upgrade sentiment scoring from `pipeline()` shortcut to full-probability FinBERT with confidence-weighted aggregation, add EMA trend endpoint, sector aggregation endpoint, and Qwen-backed narrative endpoint.
**Verified:** 2026-03-28T14:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `finbert_score()` returns `(score, confidence)` tuple; score = P(positive) - P(negative), confidence = max(softmax) | VERIFIED | `backend/main.py` lines 54-71: `def finbert_score() -> tuple`, `_finbert_infer()` computes `score = probs[0] - probs[1]`, `confidence = probs.max().item()` |
| 2 | `pipeline()` shortcut is removed; `AutoModelForSequenceClassification` is used directly | VERIFIED | `pipeline` import absent from main.py; only comment "finbert_pipe removed" at line 31; `AutoModelForSequenceClassification.from_pretrained` in lifespan at line 238 |
| 3 | `app.state.finbert_model` and `app.state.finbert_tokenizer` are set in lifespan | VERIFIED | `main.py` lines 242-243: `app.state.finbert_tokenizer = finbert_tokenizer`, `app.state.finbert_model = finbert_model` |
| 4 | `aggregate_daily_score()` applies confidence-weighted mean and excludes articles where confidence < `FINBERT_MIN_CONFIDENCE` (default 0.55) | VERIFIED | `main.py` lines 84-103: threshold filter at line 94-98, weighted mean formula at lines 101-103 |
| 5 | `FINBERT_MIN_CONFIDENCE = 0.55` added to config | VERIFIED | `backend/config.py` line 20: `finbert_min_confidence: float = 0.55` |
| 6 | `sentiment_scoring_task()` background task writes `sentiment_scores.json` every 5 minutes with 35-day pruning | VERIFIED | `main.py` lines 154-226: `_run_scoring_cycle()` groups, scores, prunes at 35 days, writes via `_write_json_atomic(SCORES_FILE, ...)`; `sentiment_scoring_task()` loops with 300s sleep |
| 7 | `GET /sentiment-trends?ticker=AAPL&window=7d` returns EMA-smoothed time series (span=5); `window=30d` uses span=20; `window=invalid` returns HTTP 400 | VERIFIED | `main.py` lines 728-759: `WINDOW_TO_SPAN = {"7d": 5, "30d": 20}`; HTTP 400 on missing span; `pd.Series.ewm(span=span).mean()` |
| 8 | `GET /sector-sentiment` excludes Real Estate (2 tickers: EQIX, SPG); includes sectors with stock_count >= 3 | VERIFIED | `main.py` lines 764-790: iterates `SECTOR_TICKERS`, `stock_count >= 3` gate; `tickers.py` confirms Real Estate = ['EQIX', 'SPG'] (2 tickers) |
| 9 | `GET /stock-narrative/{ticker}` returns `status:"complete"` on cache hit (< 1 hour); `status:"pending"` with UUID job_id on stale/missing | VERIFIED | `main.py` lines 795-833: 3600s TTL check, UTC-aware comparison, UUID via `str(uuid.uuid4())` |
| 10 | `qwen_worker()` handles job `type:"narrative"` — calls `get_qwen_narrative()`, writes to `narratives.json` | VERIFIED | `main.py` lines 459-481: `job_type = job.get("type", "analyze")`; `if job_type == "narrative"` branch calls `get_qwen_narrative()` and `_write_json_atomic(NARRATIVES_FILE, ...)` |
| 11 | `pytest backend/tests/ -x -q` exits 0 with 24 tests passing | VERIFIED | Behavioral spot-check confirms: `24 passed in 4.26s` |
| 12 | Test infrastructure: `pytest.ini` with `asyncio_mode = auto`; conftest.py with model mocks; 3 test files | VERIFIED | `backend/pytest.ini` line 2: `asyncio_mode = auto`; `conftest.py` has `mock_finbert_model`, `mock_finbert_tokenizer`, `sample_scores_data`, `sample_narratives_data` fixtures |
| 13 | `test_finbert.py` (8 tests) and `test_aggregation.py` (6 tests) are live (not skipped) | VERIFIED | All 8 tests in test_finbert.py and 6 tests in test_aggregation.py contain real assertions — no `pytest.skip()` calls |
| 14 | `test_endpoints.py` (10 tests) is live with TestClient against all 3 new endpoints | VERIFIED | All 10 tests contain real assertions using `TestClient`; `dependency_overrides[require_api_key]` bypasses auth |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|----------------|--------|
| `backend/pytest.ini` | asyncio_mode = auto, testpaths = tests | FOUND | `asyncio_mode = auto` present | Read by pytest at test run | VERIFIED |
| `backend/config.py` | `finbert_min_confidence: float = 0.55` | FOUND | Field present with comment | Imported in main.py via `get_settings()` | VERIFIED |
| `backend/main.py` | `finbert_score()` returning (score, confidence) tuple | FOUND | Full implementation with softmax, score formula, confidence | Called by `analyze_sentiment_ensemble()`, `qwen_worker()`, `_run_scoring_cycle()` | VERIFIED |
| `backend/main.py` | `aggregate_daily_score()` with confidence-weighted mean | FOUND | Full weighted mean with threshold filter, returns None on empty | Called by `_run_scoring_cycle()` | VERIFIED |
| `backend/main.py` | `sentiment_scoring_task()` + `_run_scoring_cycle()` | FOUND | Full implementation: reads news_cache, groups by (ticker, date), prunes 35 days, atomic write | Started via `asyncio.create_task()` in lifespan | VERIFIED |
| `backend/main.py` | `GET /sentiment-trends` | FOUND | EMA with span map, HTTP 400 on invalid window, returns time series list | Registered with `@app.get("/sentiment-trends")` | VERIFIED |
| `backend/main.py` | `GET /sector-sentiment` | FOUND | Iterates SECTOR_TICKERS, stock_count >= 3 gate, equal-weight mean | Registered with `@app.get("/sector-sentiment")`; reads SECTOR_TICKERS from tickers.py | VERIFIED |
| `backend/main.py` | `GET /stock-narrative/{ticker}` | FOUND | 1-hour TTL cache check, UTC-aware datetime, UUID job_id, enqueues to qwen_job_queue | Registered with `@app.get("/stock-narrative/{ticker}")` | VERIFIED |
| `backend/main.py` | `qwen_worker()` narrative branch | FOUND | job_type branching, calls get_qwen_narrative(), writes NARRATIVES_FILE atomically | Called from lifespan via `asyncio.create_task(qwen_worker())` | VERIFIED |
| `backend/tests/__init__.py` | Package marker | FOUND | Empty file (correct) | Makes tests/ a package | VERIFIED |
| `backend/tests/conftest.py` | Shared fixtures for test modules | FOUND | 4 session-scoped fixtures with torch mocks | Available to all test modules via pytest fixture injection | VERIFIED |
| `backend/tests/test_finbert.py` | 8 SENT-01 unit tests (live) | FOUND | 8 real assertions; no pytest.skip() calls | Collected by pytest from testpaths=tests | VERIFIED |
| `backend/tests/test_aggregation.py` | 6 SENT-02 unit tests (live) | FOUND | 6 real assertions including integration test for `_run_scoring_cycle()` | Collected by pytest | VERIFIED |
| `backend/tests/test_endpoints.py` | 10 SENT-03/04/05 endpoint tests (live) | FOUND | 10 real assertions; TestClient with dependency_overrides; patches _load_scores_file/_load_narratives_file | Collected by pytest | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `lifespan` | `app.state.finbert_model / finbert_tokenizer` | `AutoModelForSequenceClassification.from_pretrained` | WIRED | Lines 237-243: tokenizer and model loaded, assigned to app.state |
| `finbert_score()` | `app.state.finbert_model` | `asyncio.to_thread(_finbert_infer, text)` | WIRED | `finbert_score` calls `_finbert_infer`; `_finbert_infer` accesses `app.state.finbert_model` and `app.state.finbert_tokenizer` |
| `analyze_sentiment_ensemble()` | `finbert_score()` | `score, _ = finbert_score(text)` — tuple unpack | WIRED | Line 78: `score, _ = finbert_score(text)` |
| `sentiment_scoring_task()` | `backend/data/sentiment_scores.json` | `os.replace(tmp, SCORES_FILE)` in `_write_json_atomic` | WIRED | `_run_scoring_cycle()` calls `_write_json_atomic(SCORES_FILE, new_scores)` at line 211 |
| `GET /sentiment-trends` | `_load_scores_file()` | reads sentiment_scores.json written by sentiment_scoring_task | WIRED | Line 749: `scores = _load_scores_file().get(ticker, {})` |
| `GET /sector-sentiment` | `SECTOR_TICKERS` from tickers.py | iterates SECTOR_TICKERS to group constituent stocks | WIRED | Line 775: `for sector, tickers_in_sector in SECTOR_TICKERS.items()` |
| `GET /stock-narrative/{ticker}` | `qwen_job_queue` | `await qwen_job_queue.put({'type': 'narrative', ...})` | WIRED | Lines 828-832: job enqueued with type:"narrative" and ticker |
| `qwen_worker` | `narratives.json` | `_write_json_atomic(NARRATIVES_FILE, ...)` | WIRED | Line 475: `_write_json_atomic(NARRATIVES_FILE, narratives)` |
| `conftest.py` | `backend/main.py` | `TestClient(app)` import | WIRED | `test_endpoints.py` line 101: `import main`; line 104: `with TestClient(main.app) as client` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `GET /sentiment-trends` | `scores` dict from `_load_scores_file()` | `sentiment_scores.json` written by `_run_scoring_cycle()` every 5 min | Yes — real FinBERT scores from news articles | FLOWING |
| `GET /sector-sentiment` | `sector_scores` list from `_load_scores_file()` | Same `sentiment_scores.json` | Yes — latest date score per constituent ticker | FLOWING |
| `GET /stock-narrative/{ticker}` | `entry` from `_load_narratives_file()` | `narratives.json` written by `qwen_worker` on narrative job completion | Yes — Qwen-generated narrative text | FLOWING |
| `_run_scoring_cycle()` | `cached_news` from `news_cache.get("news", [])` | `news_cache` populated by existing news fetching pipeline | Yes — real article titles scored by FinBERT | FLOWING |

Note: At first server start before any scoring cycle runs, `sentiment_scores.json` will not exist. `_load_scores_file()` returns `{}` gracefully — endpoints return empty data rather than errors. This is correct behavior documented in Plan 03.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full pytest suite passes (24 tests) | `cd backend && python -m pytest tests/ -x -q` | `24 passed in 4.26s` | PASS |
| pytest.ini asyncio_mode | File content check | `asyncio_mode = auto` on line 2 | PASS |
| finbert_score returns tuple | grep for tuple return type annotation | `def finbert_score(text: str) -> tuple` found | PASS |
| pipeline() removed | grep for `pipeline(` in main.py | Only comment noting removal (line 31) — no import or call | PASS |
| All 3 endpoints registered | grep for `@app.get` patterns | `/sentiment-trends`, `/sector-sentiment`, `/stock-narrative/{ticker}` all registered | PASS |
| Commits exist | `git log --oneline` | All 6 Phase 4 commits confirmed: `0b3893f`, `6b19303`, `5969836`, `cbcb612`, `495698d`, `0619382` | PASS |

RuntimeWarnings about unawaited coroutines (`qwen_worker`, `sentiment_scoring_task`) at test teardown are expected — they are harmless artifacts of `patch("main.asyncio.create_task")` preventing background task startup during tests.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SENT-01 | 04-01, 04-02 | FinBERT scoring upgraded to full-probability formula: `score = P(positive) - P(negative)` using `AutoModelForSequenceClassification` | SATISFIED | `finbert_score()` in main.py; 8 unit tests green in test_finbert.py |
| SENT-02 | 04-01, 04-02 | Article-level scores aggregated using confidence-weighted mean: `Σ(score_i × conf_i) / Σ(conf_i)` | SATISFIED | `aggregate_daily_score()` in main.py; 6 unit tests green in test_aggregation.py |
| SENT-03 | 04-01, 04-03 | Sentiment trend time series per stock using EMA (span=5 for 7d, span=20 for 30d) via pandas `ewm()` | SATISFIED | `GET /sentiment-trends` with `WINDOW_TO_SPAN`; 4 endpoint tests green |
| SENT-04 | 04-01, 04-03 | Sector-level sentiment as equal-weight average of constituent stock scores; displayed only when `stock_count >= 3` | SATISFIED | `GET /sector-sentiment` with `SECTOR_TICKERS` iteration and stock_count gate; 3 endpoint tests green |
| SENT-05 | 04-01, 04-03 | Per-stock AI narrative generated by Qwen from top 8 headlines + their pre-computed scores | SATISFIED | `GET /stock-narrative/{ticker}` with 1-hour TTL, `build_narrative_prompt()`, `get_qwen_narrative()`, `qwen_worker` narrative branch; 3 endpoint tests green |

No orphaned requirements detected. All 5 SENT requirements claimed across plans 01, 02, and 03 are satisfied with implementation evidence.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/main.py` | 31 | `# finbert_pipe removed` comment | INFO | Documentation comment only — no code stub; pipeline is fully removed |

No blockers, stubs, or incomplete implementations found. The only flag is a documentation comment explaining the architectural change.

---

### Human Verification Required

#### 1. FinBERT Model Download and Real Inference

**Test:** Start the backend server (`uvicorn main:app`), wait for "Models loaded and warmed up." log, then call `GET /news` on a ticker and verify sentiment scores are non-zero floats.
**Expected:** Server loads `ProsusAI/finbert` via HuggingFace, warm-up completes without error, /news returns articles with `sentiment` field as float in [-1, 1].
**Why human:** Cannot download a 400MB+ model in automated verification. Requires network access and real GPU/CPU inference validation.

#### 2. Scoring Cycle End-to-End (After News Population)

**Test:** After news is populated in `news_cache`, wait 10 seconds for the background task delay, then check that `backend/data/sentiment_scores.json` is created and contains real ticker entries.
**Expected:** `sentiment_scores.json` exists with at least one ticker key and at least one date entry with a float value.
**Why human:** Requires a running server and populated news cache; cannot verify file creation in static analysis.

#### 3. Qwen Narrative Generation

**Test:** Call `GET /stock-narrative/AAPL` on a running server (first call should return `status:"pending"`), wait ~30 seconds, then poll `GET /qwen-results/{job_id}` for completion.
**Expected:** Job completes with `status:"complete"`, `narrative` field contains a 2-3 sentence English text about AAPL sentiment citing specific headlines.
**Why human:** Requires Qwen model (1.5B parameters) to be loaded and run inference; cannot test generation quality programmatically.

#### 4. Real Estate Exclusion at Runtime

**Test:** Call `GET /sector-sentiment` on a running server after at least one scoring cycle has completed.
**Expected:** Response JSON does NOT contain a "Real Estate" key, but does contain "Technology" (if AAPL/MSFT/NVDA/GOOGL have news).
**Why human:** Requires real scoring cycle data — the test suite patches `_load_scores_file()` with mock data; runtime behavior with actual `sentiment_scores.json` should be confirmed.

---

### Gaps Summary

No gaps. All 14 observable truths are verified. All 14 artifacts exist, are substantive (full implementations), and are wired. All 5 requirement IDs (SENT-01 through SENT-05) are satisfied. The full test suite runs `24 passed` with zero failures or skips. The `pipeline()` shortcut is fully removed with no remnant calls. All key links are confirmed by grep against the actual codebase.

---

_Verified: 2026-03-28T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
