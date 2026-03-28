# Phase 4: Sentiment Intelligence Upgrade - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the sentiment computation pipeline: replace FinBERT's top-label shortcut with full probability scoring, add time-series aggregation with EMA smoothing, compute sector-level sentiment rollups, and generate Qwen narrative summaries via the existing async job queue. This phase adds three new endpoints (`/sentiment-trends`, `/sector-sentiment`, `/stock-narrative/{ticker}`) and refactors the internal scoring function. Frontend integration is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### FinBERT Upgrade Scope
- **D-01:** Replace `pipeline()` with `AutoModelForSequenceClassification` everywhere — single scoring path for all endpoints including `/news`. No two-path maintenance burden.
- **D-02:** The new `finbert_score()` function computes `score = P(positive) - P(negative)` from the full softmax output over all three labels (positive, negative, neutral).
- **D-03:** `app.state.finbert_pipe` is replaced by `app.state.finbert_model` + `app.state.finbert_tokenizer` — no `pipeline` wrapper retained.

### Neutral Over-Classification Handling
- **D-04:** Apply a confidence threshold filter: articles where `max(softmax_output) < FINBERT_MIN_CONFIDENCE` are excluded from sentiment aggregation (SENT-02, SENT-03, SENT-04).
- **D-05:** `FINBERT_MIN_CONFIDENCE` is configurable via environment variable, defaulting to `0.55`. Add to `config.py` Settings and `.env.example`.
- **D-06:** Filtered-out articles still appear in the `/news` feed with their raw score — the threshold only affects aggregation, not display.

### Sentiment Trend Data Source
- **D-07:** Daily (ticker, date) sentiment scores persist to `backend/data/sentiment_scores.json`. File survives server restarts.
- **D-08:** A background asyncio task updates `sentiment_scores.json` every 5 minutes — independent of the `/news` fetch cycle. The task reads current news cache, scores articles, and writes aggregated daily scores.
- **D-09:** File format: `{ "AAPL": { "2026-03-28": 0.34, "2026-03-27": 0.21, ... }, ... }` — keyed by ticker then ISO date. Old entries beyond 35 days are pruned on each write.
- **D-10:** `backend/data/` directory is created by the background task on first run if it doesn't exist. Add `backend/data/*.json` to `.gitignore`.

### Narrative Caching Strategy
- **D-11:** Generated Qwen narratives persist to `backend/data/narratives.json` — keyed by ticker with an ISO timestamp field.
- **D-12:** On `GET /stock-narrative/{ticker}`, serve the cached narrative if its timestamp is less than 1 hour old. If stale or missing, enqueue a new Qwen job and return `{"status": "pending", "job_id": "..."}` — same polling pattern as `/analyze-custom`.
- **D-13:** `backend/data/narratives.json` format: `{ "AAPL": { "narrative": "...", "generated_at": "2026-03-28T10:00:00Z", "headlines_used": 8 }, ... }`.

### Claude's Discretion
- Exact Qwen prompt wording for narrative generation (must reference specific sentiment signals, not generic filler — see SENT-05 success criterion)
- Handling of tickers with fewer than 3 scored articles on a given day (skip the day or interpolate)
- Background task startup timing (delay after lifespan init to avoid contention with model warm-up)
- Error handling if `sentiment_scores.json` is corrupt on load (fall back to empty dict, log warning)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Sentiment Intelligence — SENT-01 through SENT-05 with exact formulas and endpoint specs
- `.planning/ROADMAP.md` §Phase 4 — Success criteria with acceptance conditions (neutral rate, confidence-weighted mean, EMA spans, sector threshold)

### Existing Implementation
- `backend/main.py` — Current `finbert_score()` (line 167), `qwen_worker()` (line 197), job queue pattern, TTLCache setup, lifespan context manager
- `backend/config.py` — Settings class; add `FINBERT_MIN_CONFIDENCE` here
- `backend/tickers.py` — `TICKER_DATA` (sector + market_cap per ticker), `SECTOR_TICKERS`, `ALL_TICKERS`

### State & Research Flags
- `.planning/STATE.md` §Research Flags — Qwen latency note (30–120s on CPU), sector display threshold edge cases (Energy=3, Utilities=3, Materials=1, Real Estate=2 may be at or below the ≥3 gate)

No external ADRs or design docs — all requirements are captured in REQUIREMENTS.md and the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `qwen_job_queue` + `qwen_job_results` dict + `qwen_worker()`: Reuse directly for `/stock-narrative/{ticker}` — same enqueue → poll pattern as `/analyze-custom`
- `TTLCache` from `cachetools`: Already imported; extend with `narrative_cache` if in-memory layer is needed in addition to file persistence
- `TICKER_DATA`: Has `sector` key per ticker — directly queryable for `/sector-sentiment` grouping
- `SECTOR_TICKERS`: Pre-grouped by sector — use for sector aggregation loop

### Established Patterns
- Lifespan context manager (`@asynccontextmanager async def lifespan`): Add `finbert_model`/`finbert_tokenizer` loading here alongside Qwen
- `asyncio.create_task(qwen_worker())` in lifespan: Add background sentiment scorer task the same way
- `app.state.*` for model references: Keep consistent — store new FinBERT model/tokenizer on `app.state`
- `asyncio.to_thread()`: Already used for Qwen inference — use same pattern for FinBERT tokenizer/forward pass (avoids blocking event loop)

### Integration Points
- `finbert_score()` (line 167): Replace body; all callers (`analyze_sentiment_ensemble`, `qwen_worker`) inherit the fix automatically since they call `finbert_score()`
- `/news` endpoint (line 332): `analyze_sentiment_ensemble(title)` call stays — improved automatically once `finbert_score()` is replaced
- New endpoints go in `main.py` alongside existing routes

</code_context>

<specifics>
## Specific Ideas

- Neutral threshold default of 0.55 (not 0.5) to meaningfully filter low-confidence neutral predictions without being too aggressive
- Sector display rule: `stock_count >= 3` — confirmed from REQUIREMENTS.md (SENT-04); sectors at exactly 3 (Energy, Utilities) ARE included; Real Estate (2) and Materials (1) are excluded
- Narrative must "reference specific sentiment signals, not generic filler text" — Qwen prompt should include headline titles AND their pre-computed FinBERT scores so the model can cite them

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-sentiment-intelligence-upgrade*
*Context gathered: 2026-03-28*
