# Roadmap: RealTime Stock Sentiment Analysis Engine

**Milestone:** v1.0
**Granularity:** Standard
**Coverage:** 34/34 v1 requirements mapped
**Last updated:** 2026-03-28

---

## Phases

- [x] **Phase 1: Security & Cleanup** — Eliminate active vulnerabilities and stale infrastructure before anything else is built on top of them
- [x] **Phase 2: Backend Performance** — Replace the broken async/cache foundation so the server can handle concurrent load and scale to 100 tickers
- [x] **Phase 3: Data Pipeline Expansion** — Scale from 15 to 102 S&P 100 tickers with batched fetching, tiered news, and deduplication
- [x] **Phase 4: Sentiment Intelligence Upgrade** — Replace the pipeline shortcut with full-probability FinBERT scoring, EMA trends, sector aggregation, and async Qwen narratives (completed 2026-03-28)
- [x] **Phase 5: UI Overhaul & Polish** — Build the flagship visual features (heatmap, dual-axis chart, skeleton loaders, auto-refresh) that make the portfolio story legible at a glance (completed 2026-03-29)

---

## Phase Details

### Phase 1: Security & Cleanup
**Goal**: The app is safe to make public — no hardcoded credentials, no wildcard CORS, no stale AWS wiring, and no secrets baked into Docker images.
**Depends on**: Nothing (first phase)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04
**Complexity**: M
**Success Criteria** (what must be TRUE):
  1. Running `git grep` for AWS access key patterns across the repo returns zero matches; secrets are loaded exclusively from environment variables via `pydantic-settings`
  2. Sending a CORS preflight from an unlisted origin receives a rejected response — no wildcard `*` header is returned when `allow_credentials=True` is set
  3. A request to `/analyze-custom` without a valid `X-API-Key` header returns HTTP 403, not a sentiment result
  4. A request to `/analyze-custom?text=` with a string exceeding 2000 characters returns HTTP 422 with a validation error
  5. `docker build` on both the backend and frontend images completes without baking any `.env` file into a layer — `docker history` shows no `.env` content; the frontend build reads `REACT_APP_API_URL` from the environment at runtime, not from a hardcoded AWS URL fallback
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Backend security hardening: CORS fix, API key auth, pydantic-settings, input validation (SEC-01–04)
- [ ] 01-02-PLAN.md — Docker and git hygiene: .dockerignore files, expanded .gitignore, credential scrub from fetch_latest_news.py (SEC-05, SEC-06)
- [ ] 01-03-PLAN.md — Frontend cleanup: remove hardcoded AWS URLs, remove MUI v4 + aws-amplify packages (CLEAN-01–04)

### Phase 2: Backend Performance
**Goal**: The FastAPI event loop is non-blocking, models load once before the server accepts traffic, and all cache reads respect TTL expiry.
**Depends on**: Phase 1
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05
**Complexity**: M
**Success Criteria** (what must be TRUE):
  1. The server starts and accepts requests without any 30-120 second hang — model loading happens inside the `lifespan` context manager before `yield`, not at module import
  2. A warm-up forward pass for both FinBERT and Qwen completes during startup so the first real request returns in normal inference time, not 10-50x inflated first-call latency
  3. Concurrent requests to `/stock-price` do not serialize — `run_in_executor` with `asyncio.gather` and a semaphore of 10 fans out yfinance calls in parallel; a batch of 15 tickers resolves in under 5 seconds instead of 15-30 seconds serially
  4. Cached stock data expires after 900 seconds and cached news after 300 seconds — a request made after TTL expiry triggers a fresh fetch, not a stale cache hit; the `if cached is not None:` check (not `if cached:`) handles empty-dict results correctly
  5. Submitting text to `/analyze-custom` returns a `job_id` immediately (under 200ms); polling `GET /analyze-custom/{job_id}` returns `status: "pending"` then `status: "complete"` with results when Qwen finishes — the HTTP thread is never blocked waiting for inference
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — Async refactor: lifespan model loading with warm-up, concurrent yfinance via run_in_executor+asyncio.gather+semaphore, TTLCache (900s/300s), Qwen job queue with immediate job_id response and polling endpoint

### Phase 3: Data Pipeline Expansion
**Goal**: The backend serves all 102 S&P 100 tickers organized by GICS sector, fetched efficiently in batches, with deduplicated news prioritized by market cap tier.
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Complexity**: M
**Success Criteria** (what must be TRUE):
  1. `GET /stock-price` returns data for all 102 S&P 100 tickers (including both GOOGL and GOOG, and BRK-B with hyphen normalization) organized under their GICS sector labels — the `tickers.py` module is the single source of truth for the full ticker list
  2. Stock history for all 102 tickers is fetched in 2 batched `yf.download()` calls of 50 tickers each (with a 1.5s polite delay between them), not 102 sequential `Ticker.history()` calls — total fetch time is under 10 seconds on a warm connection
  3. News fetching uses tiered priority: Tier 1 (top 20 by market cap) articles are always fetched every cycle; Tier 2 (next 40) articles rotate across cycles; Tier 3 articles are fetched only on-demand when a specific ticker page is opened
  4. Duplicate news articles that appear for multiple tickers are suppressed — each article UUID appears at most once in the news feed regardless of how many tickers it is associated with
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Create tickers.py with S&P 100 list and GICS sector/market cap mapping (DATA-01)
- [x] 03-02-PLAN.md — Refactor /stock-price to batch yf.download with sector grouping; implement tiered news rotation and UUID deduplication (DATA-02, DATA-03, DATA-04)

### Phase 4: Sentiment Intelligence Upgrade
**Goal**: Sentiment scores use the full FinBERT probability distribution, aggregate correctly over time with EMA smoothing, roll up to sector level, and produce Qwen-generated narrative summaries via a non-blocking job queue.
**Depends on**: Phase 3
**Requirements**: SENT-01, SENT-02, SENT-03, SENT-04, SENT-05
**Complexity**: L
**Success Criteria** (what must be TRUE):
  1. FinBERT scores are computed as `P(positive) - P(negative)` using `AutoModelForSequenceClassification` with full softmax output — the `pipeline()` shortcut that returned only the top-label confidence is replaced; neutral over-classification (greater than 60% neutral on a real news feed) no longer occurs at the same rate
  2. Per-stock daily sentiment is a confidence-weighted mean across all articles for that stock on that day — a high-confidence bearish article outweighs a low-confidence bullish one rather than both counting equally
  3. `GET /sentiment-trends?ticker=AAPL&window=7d` returns an EMA-smoothed sentiment time series (span=5 for 7-day, span=20 for 30-day) — the trend line is smoother than a simple rolling mean and weights recent articles more heavily
  4. `GET /sector-sentiment` returns sentiment aggregates for each GICS sector; sectors with fewer than 3 constituent stocks in the data are excluded from the response rather than shown as statistically meaningless single-ticker averages
  5. `GET /stock-narrative/{ticker}` submits a Qwen job (using the same async queue from Phase 2) that generates a concise "why is this stock moving" narrative from the top 8 headlines and their pre-computed FinBERT scores — the narrative is coherent and references specific sentiment signals, not generic filler text
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Test infrastructure: pytest setup, conftest with model mocks, stub test files for SENT-01 through SENT-05 (Wave 0)
- [x] 04-02-PLAN.md — FinBERT upgrade to full-probability scoring, config FINBERT_MIN_CONFIDENCE, confidence-weighted aggregation, background scoring task + sentiment_scores.json persistence (SENT-01, SENT-02)
- [x] 04-03-PLAN.md — Three new endpoints: /sentiment-trends (EMA, SENT-03), /sector-sentiment (exclusion rule, SENT-04), /stock-narrative/{ticker} (Qwen narrative cache, SENT-05)

### Phase 5: UI Overhaul & Polish
**Goal**: The dashboard communicates sentiment + price together at a glance through a heatmap of all 100 stocks, a dual-axis chart overlay, skeleton loaders, auto-refresh, and financial-grade visual conventions.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10
**Complexity**: L
**Success Criteria** (what must be TRUE):
  1. The homepage shows a Recharts `<Treemap>` heatmap of all 100 stocks where each cell is colored by its current sentiment score using the 5-stop diverging palette (strong positive `#16a34a` through strong negative `#dc2626`) — stocks are grouped into GICS sector regions with sector labels visible; the heatmap does not re-animate on every polling cycle
  2. The company detail page shows a dual-axis `<ComposedChart>` with price as an `<Area>` on the left Y-axis and per-day sentiment bars on the right Y-axis (domain fixed at -1 to 1) — bars are individually colored green or red by sign, and the chart remains mounted during background refresh (no blank flash)
  3. Auto-refresh runs on a 10-minute interval using a `useInterval` hook; polling pauses automatically when the browser tab is hidden; a 2px `LinearProgress` bar appears at the top of the page during a refresh cycle without dismounting any chart; a "Last updated HH:MM" timestamp is visible at all times and swaps to "Updating..." during the cycle
  4. Every data-dependent component (metric cards, charts, heatmap, news feed) shows a MUI `<Skeleton animation="wave">` placeholder that matches the content height while data is loading — there is no layout shift when data arrives; dark-theme backgrounds show the skeleton at a visible opacity
  5. All fetch failure scenarios display an informative error state with context (which endpoint failed, a retry action) rather than a blank screen or a spinner that runs forever; percent-change figures display as color-tinted pill badges (green background for positive, red for negative) using tabular-nums font rendering so columns stay aligned during live updates
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security & Cleanup | 3/3 | ✅ Complete | 2026-03-27 |
| 2. Backend Performance | 1/1 | ✅ Complete | 2026-03-28 |
| 3. Data Pipeline Expansion | 2/2 | ✅ Complete | 2026-03-28 |
| 4. Sentiment Intelligence Upgrade | 3/3 | Complete   | 2026-03-28 |
| 5. UI Overhaul & Polish | 4/4 | Complete   | 2026-03-29 |

---

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 1 | ✅ Complete |
| SEC-02 | Phase 1 | ✅ Complete |
| SEC-03 | Phase 1 | ✅ Complete |
| SEC-04 | Phase 1 | ✅ Complete |
| SEC-05 | Phase 1 | ✅ Complete |
| SEC-06 | Phase 1 | ✅ Complete |
| CLEAN-01 | Phase 1 | ✅ Complete |
| CLEAN-02 | Phase 1 | ✅ Complete |
| CLEAN-03 | Phase 1 | ✅ Complete |
| CLEAN-04 | Phase 1 | ✅ Complete |
| PERF-01 | Phase 2 | ✅ Complete |
| PERF-02 | Phase 2 | ✅ Complete |
| PERF-03 | Phase 2 | ✅ Complete |
| PERF-04 | Phase 2 | ✅ Complete |
| PERF-05 | Phase 2 | ✅ Complete |
| DATA-01 | Phase 3 | ✅ Complete |
| DATA-02 | Phase 3 | ✅ Complete |
| DATA-03 | Phase 3 | ✅ Complete |
| DATA-04 | Phase 3 | ✅ Complete |
| SENT-01 | Phase 4 | Pending |
| SENT-02 | Phase 4 | Pending |
| SENT-03 | Phase 4 | Pending |
| SENT-04 | Phase 4 | Pending |
| SENT-05 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| UI-06 | Phase 5 | Pending |
| UI-07 | Phase 5 | Pending |
| UI-08 | Phase 5 | Pending |
| UI-09 | Phase 5 | Pending |
| UI-10 | Phase 5 | Pending |

**Total v1 requirements:** 34
**Mapped:** 34
**Unmapped:** 0

---

## Dependency Chain

```
Phase 1: Security & Cleanup
    (fixes CORS exploit, removes secrets, cleans AWS wiring)
        |
        v
Phase 2: Backend Performance
    (non-blocking event loop, TTL cache, lifespan model loading, Qwen job queue)
        |
        v
Phase 3: Data Pipeline Expansion
    (100 tickers only viable on top of the async fan-out from Phase 2)
        |
        v
Phase 4: Sentiment Intelligence Upgrade
    (EMA trends and narratives require the full ticker set from Phase 3)
        |
        v
Phase 5: UI Overhaul & Polish
    (heatmap, dual-axis chart, and auto-refresh consume endpoints from Phases 3 and 4)
```

---

*Roadmap created: 2026-03-26*
*Milestone: v1.0*
