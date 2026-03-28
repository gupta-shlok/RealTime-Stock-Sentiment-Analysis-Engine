# Phase 4: Sentiment Intelligence Upgrade - Research

**Researched:** 2026-03-28
**Domain:** Transformer-based NLP scoring, time-series aggregation, async job queue, file-backed persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**FinBERT Upgrade Scope**
- D-01: Replace `pipeline()` with `AutoModelForSequenceClassification` everywhere — single scoring path for all endpoints including `/news`. No two-path maintenance burden.
- D-02: The new `finbert_score()` function computes `score = P(positive) - P(negative)` from the full softmax output over all three labels (positive, negative, neutral).
- D-03: `app.state.finbert_pipe` is replaced by `app.state.finbert_model` + `app.state.finbert_tokenizer` — no `pipeline` wrapper retained.

**Neutral Over-Classification Handling**
- D-04: Apply a confidence threshold filter: articles where `max(softmax_output) < FINBERT_MIN_CONFIDENCE` are excluded from sentiment aggregation (SENT-02, SENT-03, SENT-04).
- D-05: `FINBERT_MIN_CONFIDENCE` is configurable via environment variable, defaulting to `0.55`. Add to `config.py` Settings and `.env.example`.
- D-06: Filtered-out articles still appear in the `/news` feed with their raw score — the threshold only affects aggregation, not display.

**Sentiment Trend Data Source**
- D-07: Daily (ticker, date) sentiment scores persist to `backend/data/sentiment_scores.json`. File survives server restarts.
- D-08: A background asyncio task updates `sentiment_scores.json` every 5 minutes — independent of the `/news` fetch cycle. The task reads current news cache, scores articles, and writes aggregated daily scores.
- D-09: File format: `{ "AAPL": { "2026-03-28": 0.34, "2026-03-27": 0.21, ... }, ... }` — keyed by ticker then ISO date. Old entries beyond 35 days are pruned on each write.
- D-10: `backend/data/` directory is created by the background task on first run if it doesn't exist. Add `backend/data/*.json` to `.gitignore`.

**Narrative Caching Strategy**
- D-11: Generated Qwen narratives persist to `backend/data/narratives.json` — keyed by ticker with an ISO timestamp field.
- D-12: On `GET /stock-narrative/{ticker}`, serve the cached narrative if its timestamp is less than 1 hour old. If stale or missing, enqueue a new Qwen job and return `{"status": "pending", "job_id": "..."}` — same polling pattern as `/analyze-custom`.
- D-13: `backend/data/narratives.json` format: `{ "AAPL": { "narrative": "...", "generated_at": "2026-03-28T10:00:00Z", "headlines_used": 8 }, ... }`.

### Claude's Discretion
- Exact Qwen prompt wording for narrative generation (must reference specific sentiment signals, not generic filler — see SENT-05 success criterion)
- Handling of tickers with fewer than 3 scored articles on a given day (skip the day or interpolate)
- Background task startup timing (delay after lifespan init to avoid contention with model warm-up)
- Error handling if `sentiment_scores.json` is corrupt on load (fall back to empty dict, log warning)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SENT-01 | FinBERT scoring upgraded to `score = P(positive) - P(negative)` using `AutoModelForSequenceClassification` with full softmax | Verified: id2label is {0: positive, 1: negative, 2: neutral} from ProsusAI/finbert config.json. `outputs.logits` shape is `[batch, 3]`. `F.softmax(logits, dim=-1)` confirmed working with torch 2.11.0 + transformers 5.4.0. |
| SENT-02 | Per-stock daily sentiment aggregated as confidence-weighted mean: `Σ(score_i × conf_i) / Σ(conf_i)`, filtering articles where `max(softmax) < 0.55` | Verified: formula tested in Python; weight is `max(softmax)` (the confidence scalar). D-04/D-05 lock the threshold. |
| SENT-03 | `GET /sentiment-trends?ticker=AAPL&window=7d` returns EMA-smoothed time series (span=5 for 7d, span=20 for 30d) | Verified: `pd.Series.ewm(span=5).mean()` works in pandas 3.0.1. Window parameter maps to span via `{"7d": 5, "30d": 20}`. |
| SENT-04 | `GET /sector-sentiment` returns equal-weight sector averages; sectors with `stock_count < 3` excluded | Verified: sector counts confirmed — Real Estate (2) is the only exclusion. All other 10 sectors have 3+ stocks. `SECTOR_TICKERS` is ready to use. |
| SENT-05 | `GET /stock-narrative/{ticker}` enqueues Qwen job generating "why is this stock moving" summary from top 8 headlines + their FinBERT scores | Research confirms: reuse existing `qwen_job_queue` + `qwen_job_results` pattern. Narrative prompt must include headline text AND scores. Polling via `GET /stock-narrative/{ticker}/status/{job_id}` or same-endpoint polling. |
</phase_requirements>

---

## Summary

Phase 4 upgrades the sentiment computation pipeline on three axes: (1) the FinBERT scoring function, (2) time-series aggregation and persistence, (3) three new API endpoints. Every technical question has a verified answer based on the currently installed environment.

The key enabler is that `ProsusAI/finbert`'s `config.json` defines `id2label` as `{0: "positive", 1: "negative", 2: "neutral"}` — this is the authoritative label order. Combined with `F.softmax(logits, dim=-1)`, the formula `score = probs[0][0] - probs[0][1]` is directly implementable. The installed environment has transformers 5.4.0, torch 2.11.0 (CPU), and pandas 3.0.1 — all APIs used in this phase are confirmed available.

Persistence uses JSON files in `backend/data/`, written via `os.replace()` for near-atomic writes (confirmed available on Windows). The background scoring task is a straight `asyncio.create_task()` pattern identical to `qwen_worker()`. The three new endpoints are light wrappers over the scoring and persistence infrastructure. The sector exclusion logic is deterministic: only Real Estate (2 tickers) falls below the `stock_count >= 3` gate.

**Primary recommendation:** Implement in two plans — Plan 1 replaces `finbert_score()` and adds the background scoring task + persistence layer; Plan 2 adds the three new endpoints and the narrative Qwen job.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| transformers | 5.4.0 (installed) | `AutoModelForSequenceClassification`, `AutoTokenizer` | Already used for Qwen; replaces `pipeline()` for FinBERT |
| torch | 2.11.0+cpu (installed) | `F.softmax()`, `torch.no_grad()`, `asyncio.to_thread` inference | Already installed; CPU-only is sufficient for FinBERT |
| pandas | 3.0.1 (installed) | `Series.ewm(span).mean()` for EMA | Already in requirements.txt; standard for time-series aggregation |
| fastapi | 0.135.2 (installed) | New route handlers, Query params, HTTPException | Already the server framework |
| asyncio | stdlib | `create_task()`, `to_thread()`, `Queue` for background work | Already used for Qwen worker |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Persist/load `sentiment_scores.json` and `narratives.json` | Every background task cycle and narrative cache read |
| os / tempfile | stdlib | `os.makedirs()`, `os.replace()` for atomic writes | Background task file writes to `backend/data/` |
| datetime / timezone | stdlib | ISO date keys, 35-day pruning, 1-hour freshness check | Pruning in background task; freshness check in `/stock-narrative` |
| cachetools.TTLCache | installed | Optional in-memory layer on top of file cache | Not required for new endpoints; files are the source of truth |

### No New Dependencies Required
All required packages are already installed. No `pip install` needed for this phase.

**Version verification (installed 2026-03-28):**
```
transformers 5.4.0
torch        2.11.0+cpu
pandas       3.0.1
fastapi      0.135.2
httpx        0.28.1   (for test client)
```

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── main.py              # Replace finbert_score(); add 3 endpoints; add scoring background task
├── config.py            # Add FINBERT_MIN_CONFIDENCE setting
├── tickers.py           # No changes (SECTOR_TICKERS already correct)
├── requirements.txt     # Add pytest, pytest-asyncio (test only; no runtime additions)
└── data/                # Created at runtime by background task
    ├── sentiment_scores.json
    └── narratives.json
```

### Pattern 1: FinBERT Full-Probability Scoring

**What:** Load model and tokenizer in lifespan; call in `asyncio.to_thread()` to avoid blocking the event loop.
**When to use:** Every article scored in the `/news` endpoint and the background scoring task.

```python
# Source: ProsusAI/finbert config.json — id2label = {0: "positive", 1: "negative", 2: "neutral"}
# Source: transformers 5.4.0 docs — AutoModelForSequenceClassification.from_pretrained
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

def finbert_score(text: str) -> tuple[float, float]:
    """Return (score, confidence) where score = P(pos) - P(neg), confidence = max(softmax)."""
    try:
        inputs = app.state.finbert_tokenizer(
            text[:512],
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(app.state.finbert_model.device)
        with torch.no_grad():
            outputs = app.state.finbert_model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]  # shape: [3]
        # id2label: {0: positive, 1: negative, 2: neutral}
        score = probs[0].item() - probs[1].item()
        confidence = probs.max().item()
        return score, confidence
    except Exception as e:
        print(f"FinBERT error: {e}", flush=True)
        return 0.0, 0.0
```

Note: `finbert_score()` now returns `(score, confidence)` — a tuple. All callers must be updated. The `/news` endpoint calls `analyze_sentiment_ensemble()` which calls `finbert_score()`, so only `analyze_sentiment_ensemble()` needs updating to extract the score component.

### Pattern 2: Confidence-Weighted Mean Aggregation (SENT-02)

**What:** Aggregate per-article scores to a daily stock-level score using confidence weighting.
**When to use:** Background scoring task when computing `sentiment_scores.json`.

```python
# Source: REQUIREMENTS.md SENT-02 formula
from config import get_settings

def aggregate_daily_score(articles: list[dict]) -> float | None:
    """
    Compute confidence-weighted mean. Returns None if no articles pass threshold.
    articles: [{"score": float, "confidence": float}, ...]
    """
    settings = get_settings()
    threshold = settings.finbert_min_confidence  # default 0.55
    filtered = [(a["score"], a["confidence"]) for a in articles
                if a["confidence"] >= threshold]
    if not filtered:
        return None
    numerator = sum(s * c for s, c in filtered)
    denominator = sum(c for _, c in filtered)
    return numerator / denominator
```

### Pattern 3: Background Scoring Task (D-08, SENT-03 data source)

**What:** An asyncio task that wakes every 5 minutes, reads the news cache, scores articles per ticker per date, writes `sentiment_scores.json`.
**When to use:** Created via `asyncio.create_task()` inside the lifespan context manager, after model warm-up.

```python
# Source: Pattern derived from existing qwen_worker() in main.py (line 197)
import asyncio, json, os, tempfile
from datetime import datetime, timezone, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SCORES_FILE = os.path.join(DATA_DIR, "sentiment_scores.json")

async def sentiment_scoring_task():
    await asyncio.sleep(10)  # startup delay — avoids contention with model warm-up
    while True:
        try:
            await asyncio.to_thread(_run_scoring_cycle)
        except Exception as e:
            print(f"Scoring task error: {e}", flush=True)
        await asyncio.sleep(300)  # 5 minutes

def _run_scoring_cycle():
    """Synchronous: read news cache, score articles, write sentiment_scores.json."""
    cached_news = news_cache.get("news", [])
    if not cached_news:
        return

    # Group articles by (ticker, date)
    # ... build new_scores: dict[ticker, dict[date_str, float]]

    # Prune entries older than 35 days
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=35)).isoformat()

    # Atomic write
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(new_scores, f, indent=2)
        os.replace(tmp, SCORES_FILE)
    except Exception:
        os.unlink(tmp)
        raise
```

### Pattern 4: Sentiment Trends Endpoint (SENT-03)

**What:** Load `sentiment_scores.json`, apply EMA, return time series.
**When to use:** `GET /sentiment-trends?ticker=AAPL&window=7d`

```python
# Source: pandas 3.0.1 ewm documentation; window→span mapping from REQUIREMENTS.md SENT-03
import pandas as pd

WINDOW_TO_SPAN = {"7d": 5, "30d": 20}

@app.get("/sentiment-trends")
async def get_sentiment_trends(ticker: str, window: str = "7d"):
    span = WINDOW_TO_SPAN.get(window)
    if span is None:
        raise HTTPException(status_code=400, detail="window must be '7d' or '30d'")

    scores = _load_scores_file().get(ticker, {})
    if not scores:
        return {"ticker": ticker, "window": window, "data": []}

    series = pd.Series(scores).sort_index()  # ISO dates sort correctly
    ema = series.ewm(span=span).mean()
    return {
        "ticker": ticker,
        "window": window,
        "data": [{"date": d, "score": round(v, 4)} for d, v in ema.items()]
    }
```

### Pattern 5: Sector Sentiment Endpoint (SENT-04)

**What:** For each sector with `stock_count >= 3`, average the most recent daily score of each constituent.
**When to use:** `GET /sector-sentiment`

```python
# Source: REQUIREMENTS.md SENT-04; SECTOR_TICKERS from tickers.py
from tickers import SECTOR_TICKERS

@app.get("/sector-sentiment")
async def get_sector_sentiment():
    all_scores = _load_scores_file()
    result = {}
    for sector, tickers in SECTOR_TICKERS.items():
        sector_scores = []
        for ticker in tickers:
            ticker_dates = all_scores.get(ticker, {})
            if ticker_dates:
                latest_date = max(ticker_dates.keys())
                sector_scores.append(ticker_dates[latest_date])
        stock_count = len(sector_scores)
        if stock_count >= 3:
            result[sector] = {
                "score": round(sum(sector_scores) / stock_count, 4),
                "stock_count": stock_count,
            }
    return result
```

### Pattern 6: Stock Narrative Endpoint (SENT-05)

**What:** Check cache freshness (1 hour), serve cached narrative or enqueue Qwen job.
**When to use:** `GET /stock-narrative/{ticker}`

```python
# Source: Derived from existing /analyze-custom pattern in main.py (lines 419–432)
NARRATIVES_FILE = os.path.join(DATA_DIR, "narratives.json")

@app.get("/stock-narrative/{ticker}")
async def get_stock_narrative(ticker: str):
    narratives = _load_narratives_file()
    entry = narratives.get(ticker)
    if entry:
        generated_at = datetime.fromisoformat(entry["generated_at"])
        age_seconds = (datetime.now(timezone.utc) - generated_at).total_seconds()
        if age_seconds < 3600:
            return {"status": "complete", "ticker": ticker, **entry}

    # Stale or missing — enqueue Qwen job
    job_id = str(uuid.uuid4())
    qwen_job_results[job_id] = {"status": "pending"}
    await qwen_job_queue.put({
        "job_id": job_id,
        "type": "narrative",
        "ticker": ticker,
    })
    return {"status": "pending", "job_id": job_id}
```

The `qwen_worker()` must be extended to handle `"type": "narrative"` jobs, calling a `get_qwen_narrative(ticker, headlines, scores)` function and writing the result to `narratives.json`.

### Pattern 7: Qwen Narrative Prompt (Claude's Discretion)

**What:** Prompt structure that produces specific, signal-referencing narratives rather than generic filler.
**Recommendation:** Include ticker symbol, top 8 headlines with their FinBERT scores, and explicit instruction to cite sentiment signals.

```python
def build_narrative_prompt(ticker: str, headlines: list[dict]) -> str:
    """headlines: [{"title": str, "score": float, "date": str}, ...]"""
    headline_block = "\n".join(
        f"{i+1}. [{'+' if h['score'] > 0 else ''}{h['score']:.2f}] {h['title']}"
        for i, h in enumerate(headlines[:8])
    )
    return (
        f"You are a concise financial analyst. Below are the 8 most recent news headlines "
        f"for {ticker} with their FinBERT sentiment scores (positive=+, negative=-).\n\n"
        f"{headline_block}\n\n"
        f"Write a 2-3 sentence summary explaining what is driving {ticker}'s current sentiment. "
        f"Reference specific headlines and their sentiment signals. "
        f"Reply with only the summary text, no preamble."
    )
```

### Anti-Patterns to Avoid

- **Changing `finbert_score()` return type silently:** The function currently returns `float`. Changing it to `tuple[float, float]` will break `analyze_sentiment_ensemble()` and `qwen_worker()`. All callers must be updated in the same commit.
- **Blocking the event loop during FinBERT tokenization:** Even tokenization is CPU-bound; wrap the entire `finbert_score()` body in `asyncio.to_thread()` when called from an async context. The background task is synchronous, so no wrapping needed there.
- **Writing `sentiment_scores.json` with a plain `open()` and `json.dump()`:** A server crash mid-write produces a truncated file. Use `os.replace()` with a temp file (confirmed atomic on POSIX; near-atomic on Windows — see Pitfalls).
- **Forgetting to handle empty news cache in the scoring task:** On server startup the `news_cache` is empty. The task must check and skip gracefully on the first few cycles until news is fetched.
- **Using `datetime.now()` without `timezone.utc`:** Timezone-naive datetimes break ISO comparison with stored UTC strings. Always use `datetime.now(timezone.utc)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EMA smoothing | Custom moving average loop | `pd.Series.ewm(span=N).mean()` | Pandas ewm handles edge cases (min_periods, NaN, irregular timestamps) correctly |
| Softmax normalization | Manual `exp(x)/sum(exp(x))` | `torch.nn.functional.softmax(logits, dim=-1)` | Numerically stable; handles batch dimension |
| Atomic file writes | Custom lock files | `tempfile.mkstemp()` + `os.replace()` | `os.replace()` is atomic on POSIX and near-atomic on Windows without any locking code |
| Background task scheduling | `threading.Timer` or `schedule` library | `asyncio.create_task()` with `await asyncio.sleep(300)` | Consistent with existing `qwen_worker()` pattern; no new dependencies |
| Narrative job queue | New queue for narrative jobs | Extend existing `qwen_job_queue` with `"type"` field | Queue, worker, results dict, and polling pattern already proven |

**Key insight:** Every new component in this phase has a direct analogue in the existing codebase. The implementation is substitution and extension, not construction from scratch.

---

## Common Pitfalls

### Pitfall 1: Label Index Confusion — Wrong Scores
**What goes wrong:** Swapping positive/negative indices produces inverted scores (bearish news looks bullish).
**Why it happens:** Assuming a different label ordering than the model's actual `id2label`.
**How to avoid:** The authoritative answer (verified from `ProsusAI/finbert/config.json`): `{0: "positive", 1: "negative", 2: "neutral"}`. Use `probs[0] - probs[1]` exactly. Add an assertion in tests: `assert model.config.id2label[0] == "positive"`.
**Warning signs:** Sentiment scores near +1 for clearly negative news headlines.

### Pitfall 2: finbert_score() Return Type Change Breaks Callers
**What goes wrong:** `analyze_sentiment_ensemble()` calls `finbert_score()` and passes the result to `item['sentiment_score'] = float(fb_val)`. If `fb_val` is now a tuple, this raises `TypeError`.
**Why it happens:** Returning `(score, confidence)` tuple without updating all callers.
**How to avoid:** Search all usages of `finbert_score()` before changing its signature. Update `analyze_sentiment_ensemble()` to extract `score, conf = finbert_score(text)` and return only `score` for backward compatibility. Also update `qwen_worker()` which calls `finbert_score()` at line 204.
**Warning signs:** `TypeError: float() argument must be a string or a number, not 'tuple'` at runtime.

### Pitfall 3: news_cache Key Access Pattern
**What goes wrong:** `news_cache["news"]` raises `KeyError` on the first background task cycle (before `/news` is called).
**Why it happens:** `TTLCache` raises `KeyError` on missing keys (unlike dict `.get()`).
**How to avoid:** Use `news_cache.get("news", [])` — already the correct dict-style access. Confirmed: `TTLCache` inherits from `dict` in `cachetools`.
**Warning signs:** `KeyError: 'news'` in server logs within the first 5 minutes of startup.

### Pitfall 4: os.replace() on Windows with Open File Handles
**What goes wrong:** `os.replace(tmp, SCORES_FILE)` raises `PermissionError` on Windows if another thread/process has the target file open.
**Why it happens:** Windows does not allow renaming files that are currently open (unlike POSIX).
**How to avoid:** Keep the read side minimal — load file, process, release. Do not hold `open()` handles across `await` boundaries. For this portfolio use case (single process, single background task) this is extremely unlikely to trigger. Log a warning and skip the write if it fails rather than crashing the task.
**Warning signs:** `PermissionError: [WinError 5]` in server logs during background task writes.

### Pitfall 5: Sector Aggregation Uses Stale vs. Latest Date
**What goes wrong:** Averaging ALL historical dates per ticker instead of only the most recent date, producing a diluted sector average.
**Why it happens:** Iterating `ticker_dates.items()` instead of `ticker_dates[max(ticker_dates.keys())]`.
**How to avoid:** Always select `max(ticker_dates.keys())` for each constituent when computing sector sentiment. The endpoint represents current state, not historical average.
**Warning signs:** Sector scores unexpectedly flat or slow to respond to recent news events.

### Pitfall 6: Transformers 5.x Pipeline API Change
**What goes wrong:** The current code uses `pipeline("sentiment-analysis", model="ProsusAI/finbert", device=0 if cuda else -1)`. In transformers 5.x the `device` parameter behavior may have changed for the `pipeline()` API.
**Why it happens:** D-01 replaces `pipeline()` entirely, but if any code path retains it, it may fail.
**How to avoid:** D-01 removes `pipeline()` completely — no path should import or call it after this phase. Confirmed: `AutoModelForSequenceClassification.from_pretrained` API is unchanged in 5.4.0 (verified locally).
**Warning signs:** `TypeError` or `UserWarning` mentioning `device` parameter during lifespan startup.

### Pitfall 7: Background Task Startup Race with Model Warm-up
**What goes wrong:** The scoring task starts before `finbert_model` is loaded onto `app.state`, causing `AttributeError: 'State' object has no attribute 'finbert_model'`.
**Why it happens:** `asyncio.create_task()` in lifespan runs the coroutine concurrently with the `yield`; if the task doesn't yield first, it may start before the lifespan completes model loading.
**How to avoid:** Add `await asyncio.sleep(10)` at the top of `sentiment_scoring_task()` (Claude's Discretion item). This gives model loading time to complete before the first scoring cycle. Since model loading happens before `yield` in the lifespan, and the task is created before `yield`, the 10s delay is sufficient.
**Warning signs:** `AttributeError` during the first scoring cycle.

---

## Code Examples

### Loading FinBERT in Lifespan (Replaces pipeline)
```python
# Source: transformers 5.4.0 (installed); confirmed AutoModelForSequenceClassification available
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# In lifespan context manager:
FINBERT_MODEL_ID = "ProsusAI/finbert"
device = "cuda" if torch.cuda.is_available() else "cpu"
finbert_tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL_ID)
finbert_model = AutoModelForSequenceClassification.from_pretrained(
    FINBERT_MODEL_ID,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
)
finbert_model.to(device)
finbert_model.eval()
app.state.finbert_tokenizer = finbert_tokenizer
app.state.finbert_model = finbert_model

# Warm-up
dummy_inputs = finbert_tokenizer("Warm-up sentence.", return_tensors="pt").to(device)
with torch.no_grad():
    _ = finbert_model(**dummy_inputs)
```

### Full finbert_score() Replacement
```python
# Source: ProsusAI/finbert config.json id2label={0:positive, 1:negative, 2:neutral}
import torch.nn.functional as F

def finbert_score(text: str) -> tuple[float, float]:
    """Returns (score, confidence). score = P(pos) - P(neg). confidence = max(softmax)."""
    try:
        inputs = app.state.finbert_tokenizer(
            text[:512], return_tensors="pt", truncation=True, max_length=512
        ).to(app.state.finbert_model.device)
        with torch.no_grad():
            outputs = app.state.finbert_model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]
        return probs[0].item() - probs[1].item(), probs.max().item()
    except Exception as e:
        print(f"FinBERT error: {e}", flush=True)
        return 0.0, 0.0
```

### EMA Sentiment Trend Calculation
```python
# Source: pandas 3.0.1 — verified locally
import pandas as pd

def compute_ema_trend(ticker_scores: dict, span: int) -> list[dict]:
    """ticker_scores: {"2026-03-28": 0.34, ...}"""
    if not ticker_scores:
        return []
    series = pd.Series(ticker_scores).sort_index()
    ema = series.ewm(span=span).mean()
    return [{"date": d, "score": round(float(v), 4)} for d, v in ema.items()]
```

### Sector Counts Reference (Confirmed from tickers.py)
```
Sector                 | Tickers | Gate (>= 3) | Result
-----------------------|---------|-------------|--------
Basic Materials        |    3    |     YES     | INCLUDED (at minimum)
Communication Services |   11    |     YES     | INCLUDED
Consumer Cyclical      |    9    |     YES     | INCLUDED
Consumer Defensive     |    9    |     YES     | INCLUDED
Energy                 |    4    |     YES     | INCLUDED
Financial Services     |   18    |     YES     | INCLUDED
Healthcare             |   15    |     YES     | INCLUDED
Industrials            |   12    |     YES     | INCLUDED
Real Estate            |    2    |     NO      | EXCLUDED
Technology             |   16    |     YES     | INCLUDED
Utilities              |    3    |     YES     | INCLUDED (at minimum)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pipeline("sentiment-analysis")` returning only top-label score | `AutoModelForSequenceClassification` + manual softmax over all 3 labels | Phase 4 (now) | Eliminates top-label confidence shortcut; enables `P(pos) - P(neg)` formula |
| Equal-weight article averaging | Confidence-weighted mean | Phase 4 (now) | High-confidence articles outweigh low-confidence ones |
| No time series | EMA-smoothed daily aggregates persisted to JSON | Phase 4 (now) | Enables trend visualization in Phase 5 |
| No Qwen narratives | Async job queue with file-backed cache | Phase 4 (now) | Non-blocking; cached for 1 hour to avoid re-generation |

**Deprecated/outdated:**
- `finbert_pipe` global and `pipeline()` usage: Removed in this phase. `app.state.finbert_pipe` becomes `app.state.finbert_model` + `app.state.finbert_tokenizer`.
- `transformers pipeline device=-1`: The old CPU device parameter style; no longer needed.

---

## Open Questions

1. **News cache article-to-ticker linkage**
   - What we know: `news_cache["news"]` stores at most 20 articles after deduplication, across 60 tickers (Tier 1 + Tier 2). Articles are not tagged with which ticker sourced them.
   - What's unclear: The background scoring task needs to know which ticker each article belongs to. The current `/news` endpoint discards ticker affiliation after deduplication.
   - Recommendation: The scoring task should re-query the news cache or use a separate `ticker_news_cache` keyed by ticker. Alternatively, add a `"ticker"` field to each article during the fetch loop before deduplication. The planner should decide which approach to implement.

2. **Tickers with fewer than 3 scored articles on a given day (Claude's Discretion)**
   - What we know: Tier 3 tickers get no news in the aggregated feed; even Tier 1/2 tickers may have 0 articles on a given date.
   - What's unclear: Whether to skip those days (gaps in the trend) or carry forward the last known score.
   - Recommendation: Skip — output only dates with actual scored articles. EMA naturally handles gaps via index alignment. Gaps are preferable to fabricated carry-forward values.

3. **Qwen worker type dispatch**
   - What we know: The existing `qwen_worker()` handles `"type": None` jobs (text analysis). Adding `"type": "narrative"` requires branching.
   - What's unclear: Whether to modify the existing worker or create a second narrative-specific worker.
   - Recommendation: Modify the existing worker with an `if job.get("type") == "narrative":` branch. Keeps a single queue and single worker, consistent with D-12.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.14.3 | — |
| transformers | SENT-01: FinBERT scoring | ✓ | 5.4.0 | — |
| torch (CPU) | SENT-01: softmax, inference | ✓ | 2.11.0+cpu | — |
| pandas | SENT-03: EMA | ✓ | 3.0.1 | — |
| fastapi | New endpoints | ✓ | 0.135.2 | — |
| httpx | Test client (TestClient) | ✓ | 0.28.1 | — |
| pytest | Test runner | ✗ | — | Install: `pip install pytest pytest-asyncio` |
| pytest-asyncio | Async test support | ✗ | — | Install: `pip install pytest-asyncio` (dry-run confirmed: 1.3.0) |
| ProsusAI/finbert weights | SENT-01: model loading | ✗ (not cached) | — | Download on first run via `from_pretrained` |
| Qwen2.5-1.5B-Instruct weights | SENT-05: narratives | ✗ (not cached) | — | Download on first run via `from_pretrained` |

**Missing dependencies with no fallback:**
- Model weights (FinBERT + Qwen) require internet access on first run. No local fallback.

**Missing dependencies with fallback:**
- pytest and pytest-asyncio not installed. Wave 0 plan step must install them: `pip install pytest pytest-asyncio==1.3.0`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (not yet installed) + pytest-asyncio 1.3.0 |
| Config file | `backend/pytest.ini` — Wave 0 creates this |
| Quick run command | `pytest backend/tests/ -x -q` |
| Full suite command | `pytest backend/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SENT-01 | `finbert_score("positive text")` returns positive score; `finbert_score("negative text")` returns negative score; return type is `(float, float)` | unit | `pytest backend/tests/test_finbert.py -x` | ❌ Wave 0 |
| SENT-01 | Label order assertion: `model.config.id2label[0] == "positive"` | unit | `pytest backend/tests/test_finbert.py::test_label_order -x` | ❌ Wave 0 |
| SENT-02 | `aggregate_daily_score()` with all articles above threshold returns weighted mean; articles below threshold excluded | unit | `pytest backend/tests/test_aggregation.py -x` | ❌ Wave 0 |
| SENT-02 | `aggregate_daily_score()` returns `None` when all articles below threshold | unit | `pytest backend/tests/test_aggregation.py::test_all_below_threshold -x` | ❌ Wave 0 |
| SENT-03 | `GET /sentiment-trends?ticker=AAPL&window=7d` returns EMA series with span=5 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_7d -x` | ❌ Wave 0 |
| SENT-03 | `GET /sentiment-trends?ticker=AAPL&window=30d` returns EMA series with span=20 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_30d -x` | ❌ Wave 0 |
| SENT-03 | Invalid window parameter returns HTTP 400 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_invalid_window -x` | ❌ Wave 0 |
| SENT-04 | `GET /sector-sentiment` excludes Real Estate (2 tickers) | integration | `pytest backend/tests/test_endpoints.py::test_sector_sentiment_exclusion -x` | ❌ Wave 0 |
| SENT-04 | `GET /sector-sentiment` includes all sectors with >= 3 tickers | integration | `pytest backend/tests/test_endpoints.py::test_sector_sentiment_inclusion -x` | ❌ Wave 0 |
| SENT-05 | `GET /stock-narrative/{ticker}` returns cached narrative if < 1 hour old | integration | `pytest backend/tests/test_endpoints.py::test_narrative_cache_hit -x` | ❌ Wave 0 |
| SENT-05 | `GET /stock-narrative/{ticker}` returns `status: pending` and `job_id` when cache is stale | integration | `pytest backend/tests/test_endpoints.py::test_narrative_pending -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x -q`
- **Per wave merge:** `pytest backend/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pip install pytest pytest-asyncio==1.3.0` — test framework not installed
- [ ] `backend/pytest.ini` — configure asyncio_mode = auto
- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures: mock `app.state.finbert_model`, mock `app.state.finbert_tokenizer`, test `sentiment_scores.json`, `TestClient`
- [ ] `backend/tests/test_finbert.py` — covers SENT-01
- [ ] `backend/tests/test_aggregation.py` — covers SENT-02
- [ ] `backend/tests/test_endpoints.py` — covers SENT-03, SENT-04, SENT-05

**Testing strategy note:** FinBERT and Qwen model inference must be mocked in unit/integration tests (no 30s model load on each test run). Use `unittest.mock.patch` to replace `app.state.finbert_model` with a lightweight stub that returns fixed logits.

---

## Sources

### Primary (HIGH confidence)
- `https://huggingface.co/ProsusAI/finbert/raw/main/config.json` — Verified id2label: `{0: "positive", 1: "negative", 2: "neutral"}`
- Local environment — transformers 5.4.0, torch 2.11.0, pandas 3.0.1 confirmed installed via `pip show`
- `backend/tickers.py` — SECTOR_TICKERS counts verified locally (Real Estate=2, all others>=3)
- `backend/main.py` — `qwen_job_queue`, `qwen_worker()`, `TTLCache`, lifespan patterns confirmed
- Pandas 3.0.1 `ewm(span).mean()` — verified locally with test script
- Python stdlib `os.replace()` — confirmed available on Windows 11

### Secondary (MEDIUM confidence)
- HuggingFace ProsusAI/finbert model card — confirmed AutoModelForSequenceClassification usage pattern
- transformers v5 release blog — confirmed `from_pretrained` API unchanged; breaking changes are backend/tokenizer-level, not inference API

### Tertiary (LOW confidence)
- Qwen narrative latency: 30–120s on CPU (from STATE.md research flag — not re-measured in this session; measure before committing to `max_new_tokens=250`)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages installed and verified locally
- Architecture: HIGH — all patterns derive from existing code or locally verified library calls
- FinBERT label order: HIGH — verified directly from authoritative config.json on HuggingFace
- EMA formula: HIGH — verified locally with pandas 3.0.1
- Qwen narrative latency: LOW — only from existing STATE.md flag; not re-measured

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (30 days; all libraries are stable releases)
