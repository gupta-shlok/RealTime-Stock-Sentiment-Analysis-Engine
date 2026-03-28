# Phase 4: Sentiment Intelligence Upgrade - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 04-sentiment-intelligence-upgrade
**Areas discussed:** FinBERT upgrade scope, Sentiment trend data source, Neutral over-classification handling, Narrative caching strategy

---

## FinBERT Upgrade Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Replace everywhere | One model, one scoring path. `/news` feed also gets the improved `P(pos) - P(neg)` score. Simpler long-term. | ✓ |
| Surgical fix — new endpoints only | Keep `pipeline()` for `/news` (fast, title-level), use `AutoModel` only for SENT-01–04 endpoints. Two scoring paths to maintain. | |
| You decide | Claude picks the cleaner implementation approach | |

**User's choice:** Replace everywhere
**Notes:** Single scoring path preferred over two-path maintenance burden.

---

## Sentiment Trend Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory per session | Scores accumulate in a dict keyed by (ticker, date). Resets on restart — acceptable for portfolio demo. No extra dependencies. | |
| Lightweight JSON file on disk | Persist scores to `backend/data/sentiment_scores.json`. Survives restarts, adds file I/O. | ✓ |
| You decide | Claude picks based on what makes the demo most reliable | |

**User's choice:** Lightweight JSON file on disk
**Notes:** Survives server restarts. Follow-up: update via background task every 5 minutes (not on /news fetch), file at `backend/data/sentiment_scores.json`.

---

## Neutral Over-Classification Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Confidence threshold filter | Discard articles where `max(softmax) < FINBERT_MIN_CONFIDENCE` from aggregation. Threshold configurable via env var, default 0.55. | ✓ |
| Report raw scores as-is | No filtering. Heavy neutral bias in trend data. Phase 5 UI can show a 'low signal' indicator. | |
| Normalize distribution | Scale scores so distribution spans [-1, 1]. Distorts meaning but improves heatmap appearance. | |

**User's choice:** Confidence threshold filter
**Notes:** Default threshold 0.55, configurable via `FINBERT_MIN_CONFIDENCE` env var. Filtered articles still appear in `/news` feed — threshold only affects aggregation.

---

## Narrative Caching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory TTLCache, 1-hour TTL | `TTLCache(maxsize=102, ttl=3600)`. Fast reads, resets on restart. | |
| JSON file on disk | Store in `backend/data/narratives.json` with timestamps. Serve cached version if < 1 hour old. Survives restarts. | ✓ |
| No cache — fresh Qwen job every request | Every request triggers a new 30–120s Qwen job. Always current, but slow. | |

**User's choice:** JSON file on disk
**Notes:** User clarified they did not want in-memory caching. Consistent with sentiment_scores.json choice. Format: keyed by ticker with `narrative`, `generated_at`, and `headlines_used` fields.

---

## Claude's Discretion

- Exact Qwen prompt wording for narrative generation
- Handling of tickers with < 3 scored articles on a given day
- Background task startup timing after model warm-up
- Error handling for corrupt JSON files on load

## Deferred Ideas

None — discussion stayed within phase scope.
