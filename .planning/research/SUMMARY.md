# Project Research Summary

**Project:** RealTime Stock Sentiment Analysis Engine
**Domain:** Financial data dashboard — brownfield React 18 + FastAPI + FinBERT + Qwen2.5
**Researched:** 2026-03-26
**Confidence:** HIGH (backend, security, ticker data) / MEDIUM-HIGH (UI patterns, sentiment math)

---

## Executive Summary

This is a brownfield financial sentiment dashboard. The existing codebase has a working
architecture but contains several structural defects that block scaling to 100 tickers and
prevent safe public deployment. The research across all four areas is consistent in its
diagnosis: the problems are not design-level but implementation-level, and each has a
well-documented fix pattern. The recommended approach is a targeted refactor in dependency
order — security and cache correctness first, async concurrency second, sentiment math
improvements third, UI components fourth — rather than a rewrite.

The two biggest risks are operational: the wildcard CORS + allow_credentials=True
combination is an active security vulnerability that must be fixed before the repo is made
public, and the module-level model loading in main.py means any test import or hot-reload
hangs for 30-120 seconds. Both are two-hour fixes with high-confidence solutions.
The third systemic risk is the synchronous-inside-async event loop anti-pattern that will
freeze the server under any concurrent load — the fix (run_in_executor fan-out with a
semaphore) is equally well-documented.

The sentiment pipeline has a known accuracy gap: the current FinBERT scorer uses only the
top-label confidence score, discarding the probability distribution. The canonical
P(positive) - P(negative) formula from the FinBERT paper is a one-function replacement
that improves correctness with no added dependencies or latency. The Qwen2.5-1.5B
narrative and async job queue patterns are medium-confidence (correct for this scale but
not production-hardened at multi-worker scale) and should be validated empirically during
implementation.

---

## Key Decisions Locked by Research

These choices are settled and should be hardcoded into requirements without further debate.

### Ticker Universe

- **Use the S&P 100 (OEX) constituent list.** 100 companies, 102 tickers (GOOG + GOOGL
  both included per index methodology). Hardcode `SP100_BY_SECTOR` dict in a dedicated
  `tickers.py` module. Source: S&P Dow Jones Indices official factsheet.
- **BRK.B not BRK.A.** Use `"BRK-B"` (hyphen) in all yfinance calls.
  Apply `ticker.replace(".", "-")` normalizer before any yfinance call.
- **GEV and PLTR are current constituents** (added 2024). Verify against official
  factsheet before each major release.

### Cache Layer

- **`cachetools.TTLCache`** is the correct library. Zero dependencies. Thread-safe when
  used with `threading.Lock()`. Version 7.0.5 is current.
- **TTL values locked by research:**
  - Stock price history (1y daily bars): 900s (15 min)
  - News + FinBERT bulk sentiment: 300s (5 min)
  - Per-ticker news (on-demand): 180s (3 min)
  - Custom Qwen analysis (keyed by text hash): 3600s (1 hour)
- **The cache None-check bug must be fixed:** `if cached is not None:` not `if cached:`.
  The current `if cache["stock_data"]:` evaluates False on empty dicts, causing
  re-fetches on every request for valid-but-empty results.

### yfinance Batch Strategy

- **Use `yf.download()` with chunks of 50, not per-ticker `Ticker.history()` loops.**
  100 tickers in 2 chunks = 2 HTTP requests vs 100. Each chunk needs a 1.5s polite delay.
- **Semaphore of 10** for any remaining concurrent Ticker calls (legacy paths). Raw
  `asyncio.gather` of 100 threads will trigger Yahoo Finance 429s within seconds.
- **Catch typed exceptions:** `YFRateLimitError` and `YFPricesMissingError` from
  `yfinance.exceptions` (available since ~0.2.40). Back off 60s on rate limit errors.

### Async Architecture

- **FastAPI `lifespan` context manager** (not deprecated `@app.on_event`) for model
  loading. Official FastAPI docs pattern. Models attached to `app.state`, accessed via
  `request.app.state` in handlers.
- **Model warm-up in lifespan is mandatory.** First PyTorch inference adds 10-50x latency
  from JIT compilation. Run one dummy forward pass during startup for both FinBERT and
  Qwen before `yield`.
- **`asyncio.Queue` + background worker + polling endpoint** for Qwen inference. No new
  dependencies. Submit returns `job_id`, client polls `GET /analyze-custom/{job_id}` every
  2-5 seconds until `status == "complete"`.
- **`asyncio.Semaphore(1)` on Qwen inference.** CPU-bound with no benefit from
  parallelism; prevents OOM from concurrent requests queueing up memory.

### Sentiment Formula

- **Replace pipeline shortcut with `P(positive) - P(negative)` from full softmax output.**
  Run FinBERT directly via `AutoModelForSequenceClassification`, not `pipeline()`.
  This is the canonical formula from arXiv 1908.10063 and arXiv 2306.02136.
- **Always pass headlines to FinBERT, not full article bodies.** FinBERT is fine-tuned
  on short Financial PhraseBank sentences. Truncated 500-word articles produce worse
  results than per-sentence scoring.
- **Fallback rule for ensemble:** If Qwen fails or returns near-zero confidence, use
  FinBERT-only. Never substitute 0.0 as a fallback score — it incorrectly biases neutral.

### UI Component Choices

- **Recharts `<Treemap>` with `content={<CustomCell />}` render prop** for the sentiment
  heatmap. Use `isAnimationActive={false}` — re-animation on every poll cycle is
  distracting. Start with `size: 1` (equal sizing) because market cap data requires a
  separate API call.
- **Recharts `<ComposedChart>` with dual `<YAxis>` components** (`yAxisId="price"` left,
  `yAxisId="sentiment"` right) for the price+sentiment overlay chart. The sentiment axis
  must have `domain={[-1, 1]}` fixed — do not let it auto-scale.
- **5-stop diverging color scale** for sentiment:
  - Strong positive (+0.5 to +1.0): `#16a34a`
  - Mild positive (+0.1 to +0.5): `#4ade80`
  - Neutral (-0.1 to +0.1): `#475569`
  - Mild negative (-0.5 to -0.1): `#f87171`
  - Strong negative (-1.0 to -0.5): `#dc2626`
- **MUI `<Skeleton animation="wave">` with `bgcolor: 'rgba(255,255,255,0.06)'`** on dark
  backgrounds. The default MUI Skeleton is nearly invisible on dark themes without this
  override.
- **`useInterval` hook** (Dan Abramov canonical pattern) for auto-refresh polling with
  `setInterval`. Pass `null` as delay to pause when tab is hidden.

### Security (Non-Negotiable Before Public Deployment)

- **Fix CORS immediately.** `allow_origins=["*"]` with `allow_credentials=True` is
  invalid per the CORS spec and is an active vulnerability. Replace with explicit origin
  list from `ALLOWED_ORIGINS` environment variable.
- **`pydantic-settings` `BaseSettings`** for all config. `.env` file read once at startup
  via `lru_cache` on `get_settings()`. No per-request I/O.
- **`slowapi` for rate limiting.** `@limiter.limit("5/minute")` on `/analyze-custom`,
  `30/minute` on `/stock-price` and `/news`. `request: Request` must be the first
  parameter — slowapi silently fails to apply limits if it is absent.
- **`X-API-Key` header auth** via `APIKeyHeader` on `/analyze-custom` at minimum.
  For a portfolio demo, `/stock-price` and `/news` can remain public.
- **`text` parameter on `/analyze-custom` must be capped at `max_length=2000`.** An
  unbounded string parameter on an LLM endpoint is an OOM vector.
- **`backend/.dockerignore` and `frontend/.dockerignore` must exist** before any public
  image push. `COPY . .` without a `.dockerignore` bakes `.env` into image layers.

---

## Critical Implementation Patterns

### Backend Patterns (see BACKEND-PATTERNS.md for full code)

| Pattern | What It Does | Why Critical |
|---------|-------------|--------------|
| `lifespan` + `app.state` | Load models once, attach to app | Eliminates 30-120s import blocking |
| `run_in_executor` + `asyncio.gather` | Fan out yfinance calls concurrently | 15-30s serial → 2-4s parallel |
| `asyncio.Semaphore(10)` on yfinance | Cap concurrent Yahoo Finance calls | Prevents 429 rate limit errors |
| `asyncio.Queue` + background worker | Decouple Qwen from HTTP cycle | Prevents 30-120s HTTP timeouts |
| `cachetools.TTLCache` + `threading.Lock` | TTL-bounded in-memory cache | Prevents stale data and thread corruption |
| `pydantic-settings` + `lru_cache` | Centralized env config | Single `.env` read, testable, type-safe |

### Sentiment Patterns (see SENTIMENT-PATTERNS.md for full code)

| Pattern | What It Does | Why Critical |
|---------|-------------|--------------|
| `P(pos) - P(neg)` normalization | Full probability extraction from FinBERT | Pipeline shortcut discards signal |
| Confidence-proportional ensemble | Weight by each model's certainty | Outperforms fixed 60/40 on ambiguous inputs |
| EMA with span=5 (7d) and span=20 (30d) | Sentiment trend smoothing | Simple rolling mean treats old news as fresh |
| Recency decay with 24h half-life | Article-level time weighting | Real-time aggregation without daily bucketing |
| News deduplication by UUID | De-dup across tickers | Macro articles appear for every ticker |
| Equal-weight sector aggregation | Sector-level sentiment roll-up | Small-caps are more sentiment-reactive |

### UI Patterns (see UI-PATTERNS.md for full code)

| Pattern | What It Does | Why Critical |
|---------|-------------|--------------|
| `SentimentCell` custom Treemap content | Per-cell color by sentiment | Recharts default has no color-by-data |
| Dual `yAxisId` ComposedChart | Price and sentiment on incompatible scales | Auto-scale breaks the sentiment axis |
| Per-`Cell` fill in `<Bar>` | Green/red bars by sign | Default uniform bar color loses signal |
| `useInterval(fetchData, delay \|\| null)` | Pausable polling | Prevents background tab API waste |
| `LinearProgress height: 2px` | Non-disruptive refresh indicator | Never unmount charts during refresh |
| `font-variant-numeric: tabular-nums` | Stable number column alignment | Numbers jitter on update without it |
| Skeleton `height` matched to content | Prevents layout shift on data arrival | CLS makes dashboards feel broken |

### Security Patterns (see DATA-SECURITY.md for full code)

| Pattern | What It Does | Why Critical |
|---------|-------------|--------------|
| Explicit CORS origin list from env var | Replaces wildcard | Wildcard + credentials = CORS exploit |
| `APIKeyHeader` dependency | Protects LLM endpoint | Anyone can trigger Qwen inference otherwise |
| `Query(max_length=2000)` on text | Bounds LLM input | Prevents OOM from huge strings |
| `Query(pattern=r'^[A-Z0-9.\-]{1,10}$')` on ticker | Validates ticker shape | Rejects injection strings |
| Ticker whitelist check against SP100_TICKERS | Validates ticker semantics | Prevents arbitrary yfinance calls |
| `.dockerignore` + runtime `env_file` | Keeps secrets out of image layers | Build-time baking = permanent secret exposure |

---

## Dependency Order (What Must Be Built Before What)

This is the correct implementation order based on cross-cutting dependencies between research areas.

```
1. SECURITY FOUNDATION
   Fix CORS wildcard + add pydantic-settings config
   Add .dockerignore to backend and frontend
   Add input validation (ticker pattern, text max_length)
        |
        v
2. CACHE + ASYNC REFACTOR
   Replace dict cache with cachetools.TTLCache + threading.Lock
   Move model loads into lifespan context manager
   Convert sync yfinance loops to async run_in_executor fan-out with Semaphore(10)
   Add rate limiting with slowapi
        |
        v
3. TICKER EXPANSION
   Add SP100_BY_SECTOR dict in tickers.py
   Replace existing 15-ticker list with SP100_TICKERS
   Switch from per-ticker Ticker.history() to yf.download() chunked batches
   Add news tiering (Tier 1 always, Tier 2 on rotation, Tier 3 on-demand)
   Add news deduplication by UUID
        |
        v
4. SENTIMENT MATH UPGRADE
   Replace pipeline() with AutoModelForSequenceClassification for full probs
   Implement P(pos) - P(neg) normalization
   Add confidence-proportional ensemble blend with FinBERT fallback
   Implement asyncio.Queue + worker for Qwen (submit + poll endpoints)
   Add daily_stock_scores() and EMA trend functions
   Add GICS sector mapping and equal-weight sector aggregation
        |
        v
5. NEW API ENDPOINTS
   GET /sentiment-trends?ticker=X&window=7d
   GET /stock-narrative/{ticker}  (Qwen narrative, via job queue)
   GET /sector-sentiment
   GET /health  (no auth, for reviewer signal)
        |
        v
6. UI COMPONENTS
   SentimentHeatmap with Recharts Treemap + SentimentCell
   StockChart upgrade to ComposedChart + dual YAxis
   Skeleton loaders for all major components
   useInterval auto-refresh + page visibility pause
   Last-updated indicator
   Section header typography (all-caps + letter-spacing)
   Change badge with colored pill background
```

**Why this order matters:**
- Security before anything else — the CORS bug can be exploited the moment the app is
  deployed; it takes 30 minutes to fix.
- Cache correctness before async refactor — the async refactor calls `set_cached_stock_data`
  which needs the new TTLCache API; both changes touch the same lines.
- Ticker expansion after async refactor — expanding to 100 tickers with the old serial
  loop would make the app unusable; the fan-out pattern must exist first.
- Sentiment math before new endpoints — the new API endpoints return EMA trends and
  narratives; those functions must exist before the routes.
- UI last — the frontend depends on all the new API endpoints; building UI before the
  endpoints exist means mocking or stubbing that must be undone.

---

## Risks and Open Questions

### High Confidence (implement as specified)

- FinBERT `P(pos) - P(neg)` formula — stated explicitly in the paper
- `yf.download()` batch vs per-ticker loop — verified against yfinance source
- `lifespan` context manager pattern — official FastAPI docs
- `cachetools.TTLCache` thread-safety with `threading.Lock` — verified against library docs
- CORS wildcard + credentials is invalid — per the W3C CORS spec and FastAPI docs
- S&P 100 ticker list (102 symbols) — verified against official S&P factsheet

### Medium Confidence (implement, then validate empirically)

- **`asyncio.Queue` job queue for Qwen** — correct for single-process portfolio deployment
  but not battle-tested at any scale. If concurrent submissions pile up and the worker
  crashes, all queued jobs are lost. Validate recovery behavior during testing.
- **Qwen2.5-1.5B narrative quality on 8-headline prompts** — prompt templates are
  synthesized from 2024-2025 prompting literature but not benchmarked on this exact
  use case. Quality may vary; add few-shot examples if outputs are poor.
- **`temperature=0.3` for narrative vs `do_sample=False` for classification** — correct
  directionally but optimal values need empirical tuning for the 1.5B model.
- **Sector label thresholds (0.05 / 0.15)** — heuristic with no published benchmark.
  Treat as starting point; adjust based on actual score distributions observed.
- **24h half-life for recency decay** — general EWM theory applied to news; limited
  financial-specific validation. Berkeley 2024 found decay did not improve price
  prediction, but it is appropriate for descriptive aggregation (the goal here).
- **Yahoo Finance rate limits** — informal community observations suggest ~200-400
  req/hour. Exact limits are not documented. The 2-chunk + 1.5s delay strategy is
  conservative but may still hit limits if cache misses occur concurrently.

### Low Confidence (needs validation before committing)

- **Qwen narrative generation CPU latency** — documented as 30-120s on CPU for 100
  tokens at 1-3 t/s, but actual latency depends heavily on the host machine. Measure
  before choosing `max_new_tokens=250` for narratives — this could be 2-4 minutes.
- **FinBERT neutral over-classification** — the research warns > 60% neutral is a signal
  of the pipeline problem, but the threshold is a rule of thumb. Run distribution analysis
  on real data after implementing full-prob scoring to validate.

### Open Questions

1. Should `/stock-price` be gated with API key auth, or remain public for the demo?
   Research recommends public for portfolio reviewers but with rate limiting. Decide
   before deployment.
2. Should the heatmap use equal sizing (easier, ships faster) or volume sizing (more
   interesting, requires additional yfinance call for volume data)?
3. Is a separate sub-panel (Bloomberg style) or dual-axis overlay (current plan) better
   for the price+sentiment chart? Both patterns are documented; dual-axis is the current
   spec but separate panels are cleaner at longer time windows.

---

## What NOT to Do

Anti-patterns explicitly warned against across all four research files.

### Backend Anti-Patterns

- **Do not use `async def` handlers with direct sync calls inside them.** `yf.Ticker().history()` inside `async def get_stock_price()` blocks the event loop and serializes all requests. Use `run_in_executor` or convert to `def` (sync).
- **Do not use `yf.download()` for concurrent calls with different tickers in the same process.** `yf.download()` uses module-level shared dicts (`_DFS`, `_ERRORS`) that are not thread-safe. For concurrent paths, use `yf.Ticker(ticker).history()` per-instance.
- **Do not use `ProcessPoolExecutor` for Qwen inference.** Requires model serialization (pickle) between processes or re-loading 2-3GB per worker. `ThreadPoolExecutor` + `Semaphore(1)` is correct — PyTorch releases the GIL during C-extension forward passes.
- **Do not use `BackgroundTasks` for Qwen.** `BackgroundTasks` is fire-and-forget with no way to retrieve results. The client needs to poll for the result.
- **Do not use `aiocache` instead of `cachetools`.** `aiocache` is appropriate for async-only code; this app has both sync and async paths. `cachetools` with a lock is simpler and has fewer moving parts.

### Sentiment Anti-Patterns

- **Do not use the `pipeline()` API score as the sentiment value.** `pipeline()` returns only the top-label probability, discarding the full distribution. This overstates confidence on ambiguous inputs.
- **Do not pass full article bodies to FinBERT.** FinBERT was fine-tuned on short sentences. Truncated articles score worse than headlines.
- **Do not treat 0.0 as a safe Qwen fallback score.** 0.0 biases the ensemble toward neutral. Fall back to FinBERT-only.
- **Do not build sector sentiment from fewer than 3 stocks.** A 1-2 ticker "sector" is not statistically meaningful. Gate sector display on `stock_count >= 3`.
- **Do not use simple rolling mean for sentiment trends.** SMA weights 30-day-old articles identically to today's. Use EMA.

### UI Anti-Patterns

- **Do not unmount charts or the heatmap during background refresh.** The current `NewsData.js` pattern that returns `<div>Fetching...</div>` while loading is explicitly wrong for auto-refresh. Update state in-place; use a 2px `LinearProgress` bar for in-progress feedback.
- **Do not use blue/teal for positive financial change.** Financial convention is green=positive, red=negative. Using the project's `#3b82f6` accent for price gains will confuse users and look non-professional.
- **Do not use the Recharts default tooltip for dual-axis charts.** The default tooltip does not know axis assignments. Always write a custom `content` component for `ComposedChart`.
- **Do not animate the Treemap on polling cycles.** Set `isAnimationActive={false}` on `<Treemap>`. Re-animation every 60 seconds is visually disruptive.
- **Do not poll when the tab is hidden.** Pass `null` as the `useInterval` delay when `document.visibilityState === 'hidden'`.

### Security Anti-Patterns

- **Do not commit `.env` files.** Git history is permanent. If secrets have been committed, rotate them immediately even if the commit was later deleted.
- **Do not use `allow_origins=["*"]` with `allow_credentials=True`.** This is both invalid per spec and an active security vulnerability.
- **Do not pass build-time secrets via Docker `ARG`.** They are stored in image layers and visible in `docker history`. Use `env_file` in docker-compose for runtime injection.
- **Do not skip `request: Request` as the first parameter on slowapi-decorated routes.** Slowapi silently fails to apply rate limits if `request` is absent — no error, no warning.

---

## Implications for Roadmap

### Phase 1: Security and Foundation Hardening
**Rationale:** Two critical vulnerabilities (CORS exploit, no input validation) must be fixed before anything else is built on top of them. They also unblock all other phases — rate limiting is needed before ticker expansion, and config management is needed before adding new env vars.
**Delivers:** Production-safe backend, correct config management, .dockerignore files, .env.example template
**From research:** DATA-SECURITY.md Issues 1-5, BACKEND-PATTERNS.md Section 5
**Must avoid:** Committing .env files, `allow_origins=["*"]` + credentials, unbounded text parameter

### Phase 2: Cache Correctness and Async Refactor
**Rationale:** The async/blocking bug affects every endpoint. The cache TTL bug affects every response. Both must be fixed before expanding the ticker universe — scaling to 100 tickers on a broken async foundation makes debugging impossible.
**Delivers:** Non-blocking event loop, correct TTL caching, model loaded via lifespan with warm-up
**From research:** BACKEND-PATTERNS.md Sections 1-4, DATA-SECURITY.md Section 2
**Must avoid:** `async def` with sync calls inside, `if cache["key"]:` falsy check, module-level model loading

### Phase 3: S&P 100 Ticker Expansion and Data Pipeline
**Rationale:** Ticker expansion depends on the async refactor (Phase 2) being in place. The batched yfinance download and tiered news fetching are new subsystems that build on the corrected async foundation.
**Delivers:** All 102 S&P 100 tickers in stock data, tiered news fetching (Tier 1 always, Tier 2 rotating), news deduplication, BRK-B normalization
**From research:** DATA-SECURITY.md Sections 1-3, BACKEND-PATTERNS.md Section 4
**Must avoid:** Per-ticker Ticker.history() loops at this scale, unfenced `asyncio.gather` of 100 calls, no deduplication

### Phase 4: Sentiment Math Upgrade and New Analysis Endpoints
**Rationale:** Sentiment math improvements require the updated FinBERT model access pattern (full probs, not pipeline). The Qwen job queue depends on the lifespan-based model loading from Phase 2. New endpoints depend on the new sentiment functions.
**Delivers:** Full-probability FinBERT scoring, EMA sentiment trends, sector aggregation, Qwen narrative via async job queue, four new API endpoints
**From research:** SENTIMENT-PATTERNS.md Sections 1-7, BACKEND-PATTERNS.md Section 2
**Must avoid:** FinBERT pipeline shortcut, fixed 60/40 blend on failing Qwen calls, 0.0 as fallback score, ProcessPoolExecutor for Qwen

### Phase 5: UI Components and Dashboard Polish
**Rationale:** All UI work depends on the new endpoints being available. This phase converts the existing component structure into a professional financial dashboard.
**Delivers:** Sentiment heatmap (Treemap), dual-axis price+sentiment chart, skeleton loaders, auto-refresh with visibility pause, last-updated indicators, financial typography conventions
**From research:** UI-PATTERNS.md Sections 1-5, SENTIMENT-PATTERNS.md Section 5 (sector display)
**Must avoid:** Unmounting charts on refresh, blue for positive change, default Recharts tooltip on dual-axis, animated Treemap on poll cycles, polling on hidden tabs

### Phase Ordering Rationale

- Security must be first because the CORS vulnerability is exploitable in the current state and Phase 3's ticker expansion increases the attack surface.
- The cache and async refactor is Phase 2 because every subsequent phase (ticker expansion, sentiment, UI polling) depends on a non-blocking event loop and correct caching.
- Ticker expansion is Phase 3 rather than Phase 5 because the sentiment aggregation math (Phase 4) requires a meaningful number of tickers to produce sector-level signals.
- Sentiment math is Phase 4 because the new UI components (Phase 5) display EMA trends and narratives that do not exist until Phase 4 delivers them.
- UI is last because it is the only purely additive phase — it does not change backend contracts, it consumes them.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 4 (Qwen job queue):** The asyncio.Queue worker has no persistence. If the server restarts mid-job, the result is lost. Planning should decide whether to add a simple file-based checkpoint or accept this limitation for portfolio scope.
- **Phase 4 (Qwen narrative latency):** The actual CPU latency of `max_new_tokens=250` on the host machine needs measurement before the UI polling interval is chosen. If latency exceeds 3 minutes, the polling UX needs rethinking.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (security):** All patterns are explicit in research. CORS fix, pydantic-settings, APIKeyHeader, slowapi — these are copy-and-adapt, not design decisions.
- **Phase 2 (cache/async):** lifespan, TTLCache, run_in_executor — these are official FastAPI patterns with no ambiguity.
- **Phase 5 (UI components):** Recharts Treemap, ComposedChart, MUI Skeleton — all have verified implementation patterns in the research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| S&P 100 ticker list | HIGH | Verified against official S&P Dow Jones factsheet |
| yfinance batch strategy | HIGH | Verified against yfinance GitHub source and DeepWiki |
| FastAPI lifespan + app.state | HIGH | Official FastAPI documentation |
| cachetools TTLCache | HIGH | PyPI documentation; v7.0.5 current |
| CORS fix (wildcard + credentials) | HIGH | Per W3C CORS spec, FastAPI docs, explicit warning |
| FinBERT P(pos)-P(neg) formula | HIGH | Stated in FinBERT paper arXiv 1908.10063 |
| EMA/EWMA sentiment smoothing | HIGH | Pandas ewm() docs + financial research consensus |
| GICS sector structure | HIGH | S&P/MSCI official GICS documentation |
| Recharts Treemap + ComposedChart | HIGH (patterns) / MEDIUM (dual-axis details) | Official Recharts docs; dual-axis verified via community sources |
| MUI Skeleton dark theme fix | HIGH | Verified against MUI GitHub issue #19957 |
| slowapi rate limiting | HIGH | Official slowapi GitHub; multiple 2025-2026 tutorials |
| asyncio.Queue job queue | MEDIUM | Correct for portfolio single-process; not production-tested at scale |
| Qwen narrative prompt templates | MEDIUM | Synthesized from prompting literature; not benchmarked on this model |
| Recency decay half-life values | MEDIUM | General EWM theory; limited financial-specific benchmarks |
| Sector label thresholds | LOW | Heuristic; no published benchmark for these values |
| Yahoo Finance rate limits | MEDIUM | Community observations; no official documentation |

**Overall confidence:** HIGH for the refactor scope. MEDIUM for the new sentiment features.

### Gaps to Address During Implementation

1. **Qwen CPU latency on this machine:** Measure actual tokens/second during Phase 2 warm-up. If below 1 t/s, reduce `max_new_tokens` to 150 and adjust polling interval to 10s.
2. **FinBERT neutral over-classification rate:** After implementing full-prob scoring, run against the real news feed and check if neutral > 60% of articles. If so, apply the `p_positive + p_negative > 0.4` override rule from SENTIMENT-PATTERNS.md Section 8.
3. **Yahoo Finance news API deduplication in production:** The UUID-based deduplication assumes Yahoo assigns stable UUIDs. Validate that repeated calls return the same UUID for the same article before relying on it for all 100 tickers.
4. **Sector coverage with current ticker list:** With 102 tickers, Energy (3), Real Estate (2), Utilities (3), and Materials (1) all fall below the `stock_count >= 3` sector display threshold. Plan for either displaying partial sectors with a caveat or suppressing them from the sector view.

---

## Sources

### Primary (HIGH confidence)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) — lifespan context manager, app.state
- [FastAPI CORS Docs](https://fastapi.tiangolo.com/tutorial/cors/) — wildcard + credentials constraint
- [FastAPI Concurrency](https://fastapi.tiangolo.com/async/) — run_in_executor, sync vs async handlers
- [FinBERT paper (arXiv 1908.10063)](https://arxiv.org/abs/1908.10063) — P(pos) - P(neg) formula
- [FinBERT Application (arXiv 2306.02136)](https://arxiv.org/html/2306.02136v3) — confidence-weighted aggregation
- [cachetools PyPI](https://pypi.org/project/cachetools/) — TTLCache API, thread safety
- [slowapi GitHub](https://github.com/laurentS/slowapi) — rate limiting patterns
- [S&P 100 Official Factsheet](https://www.spglobal.com/spdji/en/indices/equity/sp-100/) — ticker list
- [yfinance DeepWiki](https://deepwiki.com/ranaroussi/yfinance/4.2-working-with-multiple-tickers) — batch download patterns
- [yfinance thread safety issue #2557](https://github.com/ranaroussi/yfinance/issues/2557) — per-instance vs download() safety
- [MUI Skeleton](https://mui.com/material-ui/react-skeleton/) — variant/animation API
- [MUI dark theme issue #19957](https://github.com/mui/material-ui/issues/19957) — bgcolor override
- [Recharts GitHub Treemap demo](https://github.com/recharts/recharts/blob/2.x/demo/component/Treemap.tsx) — data shape, content prop
- [S&P/MSCI GICS Standard](https://www.spglobal.com/spdji/en/landing/topic/gics/) — 11-sector structure
- [pandas ewm() docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html) — EMA implementation

### Secondary (MEDIUM confidence)
- [JamWithAI: Concurrency Mistake in FastAPI AI Services](https://jamwithai.substack.com/p/the-concurrency-mistake-hiding-in) — async/sync blocking pattern
- [Berkeley MIDS 2024: Sentiment Analysis for Financial Markets](https://www.ischool.berkeley.edu/projects/2024/sentiment-analysis-financial-markets) — daily aggregation
- [Nature/Humanities 2024: Aggregating Investor Sentiment](https://www.nature.com/articles/s41599-024-03434-2) — equal vs market-cap weighting
- [RavenPack S&P 500 Sentiment Index Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-500-rvnpck-ai-sentiment-indices.pdf) — sector aggregation
- [GitGuardian: Secrets in Docker](https://blog.gitguardian.com/how-to-handle-secrets-in-docker/) — env_file vs build ARG
- [TanStack Query auto-refetching](https://tanstack.com/query/v5/docs/framework/react/examples/auto-refetching) — refetchInterval pattern
- [Cloudscape loading patterns](https://cloudscape.design/patterns/general/loading-and-refreshing/) — last-updated, non-disruptive refresh
- [Bloomberg color accessibility](https://www.bloomberg.com/company/stories/designing-the-terminal-for-color-accessibility/) — colorblind-safe palette

### Tertiary (LOW confidence / heuristic)
- Sector label thresholds (0.05/0.15) — synthesized heuristic, needs empirical validation
- Recency decay half-lives (24h/72h) — general EWM theory applied to news domain
- Qwen narrative prompt templates — synthesized from 2024-2025 prompting literature

---
*Research completed: 2026-03-26*
*Synthesized by: gsd-synthesizer*
*Ready for roadmap: yes*
