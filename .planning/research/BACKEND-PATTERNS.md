# Backend Patterns Research: FastAPI + ML Model Serving

**Project:** RealTime-Stock-Sentiment-Analysis-Engine
**Researched:** 2026-03-26
**Overall Confidence:** HIGH (all patterns verified against official docs and multiple current sources)

---

## Context: What the Current Code Does Wrong

Before diving into patterns, here is a precise diagnosis of the three structural problems in `backend/main.py` that this document addresses:

| Problem | Location | Consequence |
|---------|----------|-------------|
| Module-level blocking model load | Lines 36-58 | `import` of main.py blocks for 30-120s; any hot-reload or test import hangs |
| `async def` handlers with sync yfinance | Lines 161, 210, 257 | Blocking calls inside the event loop — one slow request freezes all others |
| No-TTL dict cache | Lines 144-148 | Cache never expires; stale data served indefinitely after first load |

---

## Section 1: Async ML Model Loading — FastAPI Lifespan Pattern

### Why the Current Approach Fails

The models are loaded at module scope (top-level `pipeline(...)` and `from_pretrained(...)` calls). This means:
- The event loop is not yet running when models load, so you cannot use async I/O during startup.
- Uvicorn worker startup blocks entirely until both models are loaded.
- In tests or multi-worker deployments, every process re-loads models at import time.

### The Fix: `lifespan` Context Manager + `app.state`

FastAPI's `lifespan` parameter (stable since FastAPI 0.93, replacing deprecated `@app.on_event`) accepts an async context manager. Code before `yield` runs once before the app accepts any requests. Code after `yield` runs on shutdown.

**Confidence: HIGH** — This is the pattern shown in the official FastAPI documentation.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading models on device: {device}", flush=True)

    # FinBERT loads fast (~2-5s), load synchronously inside a thread
    # so we don't block the event loop if this is awaited elsewhere
    loop = asyncio.get_running_loop()

    finbert = await loop.run_in_executor(
        None,  # uses default ThreadPoolExecutor
        lambda: pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=0 if device == "cuda" else -1,
        )
    )

    qwen_tokenizer = await loop.run_in_executor(
        None,
        lambda: AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
    )

    qwen_model = await loop.run_in_executor(
        None,
        lambda: AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-1.5B-Instruct",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto",
        )
    )

    # --- WARM-UP ---
    # Run one dummy inference to force JIT compilation and
    # eliminate first-request latency spikes (10-50x on PyTorch)
    _dummy = finbert("Market conditions are stable.")
    with torch.no_grad():
        _dummy_inputs = qwen_tokenizer("test", return_tensors="pt").to(qwen_model.device)
        qwen_model.generate(**_dummy_inputs, max_new_tokens=1)
    print("Models warmed up and ready.", flush=True)

    # Attach to app.state so every request handler can reach them
    app.state.finbert = finbert
    app.state.qwen_tokenizer = qwen_tokenizer
    app.state.qwen_model = qwen_model
    app.state.device = device

    yield  # Application runs here

    # --- SHUTDOWN ---
    # Release GPU/CPU memory
    del app.state.finbert
    del app.state.qwen_model
    torch.cuda.empty_cache()
    print("Models unloaded.", flush=True)


app = FastAPI(lifespan=lifespan)
```

### Accessing Models in Route Handlers

Use `request.app.state` to reach the models without global variables:

```python
@app.get("/analyze-custom")
async def analyze_custom(text: str, request: Request):
    finbert = request.app.state.finbert
    qwen_model = request.app.state.qwen_model
    qwen_tokenizer = request.app.state.qwen_tokenizer
    # ... rest of handler
```

### Why `run_in_executor` Inside Lifespan?

`from_pretrained` does disk I/O and some CPU work. Wrapping it in `run_in_executor` keeps the startup code async-compatible and means that if you later add health-check polling during startup, those coroutines can still run. For a simple single-worker server this is minor, but it is the correct pattern.

### Warm-up Rationale

PyTorch uses lazy compilation. The first inference call triggers kernel compilation, JIT tracing, and CUDA graph construction — adding 10-50x latency to the first real request. Running one dummy forward pass during `lifespan` startup eliminates this entirely. Use an input representative of real requests (400-512 tokens for this project).

---

## Section 2: Background Task Queues for Slow Inference

### The Problem: Qwen2.5-1.5B on CPU Takes 30-120 Seconds

`/analyze-custom` calls `get_qwen_analysis()` synchronously. On CPU, this generates 100 tokens at approximately 1-3 tokens/second — meaning the HTTP request hangs for 30-120 seconds. HTTP clients will typically timeout at 30-60 seconds. Even if they don't, the endpoint monopolizes the event loop's thread pool slot for that entire duration.

### Decision Matrix for a Single-Server Portfolio Project

| Option | Fit for This Project | Reason |
|--------|---------------------|--------|
| `BackgroundTasks` (built-in) | No | Fire-and-forget only; client cannot poll for result |
| `asyncio.Queue` + worker task | Yes — simplest | Pure in-process; no Redis; suits portfolio scale |
| ARQ + Redis | Overkill | Adds Redis dependency; better for multi-worker |
| Celery + Redis/RabbitMQ | Overkill | Sync-first; adds significant operational overhead |

**Recommendation: `asyncio.Queue` + background worker task + polling endpoint.** This keeps the stack to zero new dependencies while properly decoupling the slow inference from the HTTP response cycle.

**Confidence: MEDIUM** — ARQ is the production-correct answer at scale; asyncio.Queue is the correct answer for a single-process, single-worker portfolio deployment that must avoid Redis.

### Implementation: In-Process Job Queue

```python
import asyncio
import uuid
from typing import Dict, Any

# Job store — in production replace with Redis
job_store: Dict[str, Any] = {}
inference_queue: asyncio.Queue = asyncio.Queue()

# Semaphore: only 1 Qwen inference at a time (CPU-bound, no benefit from parallelism)
_inference_sem = asyncio.Semaphore(1)


async def inference_worker():
    """
    Long-running asyncio task. Started once in lifespan, runs until shutdown.
    Pulls jobs off the queue and runs Qwen inference in a thread executor
    so it never blocks the event loop.
    """
    loop = asyncio.get_running_loop()
    while True:
        job_id, text = await inference_queue.get()
        job_store[job_id] = {"status": "running"}
        try:
            async with _inference_sem:
                # Run the blocking torch call in a thread so the event
                # loop can still handle health-checks and /stock-price
                # during the 30-120s inference window.
                qwen_val, reasoning = await loop.run_in_executor(
                    None, get_qwen_analysis_sync, text
                )
            fb_val = finbert_score_sync(text)  # fast, can run in same thread
            blended = round(0.6 * fb_val + 0.4 * qwen_val, 4)
            job_store[job_id] = {
                "status": "complete",
                "score": blended,
                "label": label_from_score(blended),
                "finbert_score": round(fb_val, 4),
                "llm_score": round(qwen_val, 4),
                "reasoning": reasoning,
                "model": "FinBERT + Qwen2.5-1.5B-Instruct Ensemble",
            }
        except Exception as e:
            job_store[job_id] = {"status": "error", "detail": str(e)}
        finally:
            inference_queue.task_done()


# In your lifespan, after models are loaded:
# asyncio.create_task(inference_worker())
```

### Updated `/analyze-custom` Endpoint (Submit + Poll)

```python
@app.post("/analyze-custom")
async def submit_analysis(text: str):
    """Submit text for ensemble analysis. Returns a job_id to poll."""
    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "queued"}
    await inference_queue.put((job_id, text))
    return {"job_id": job_id, "status": "queued"}


@app.get("/analyze-custom/{job_id}")
async def get_analysis_result(job_id: str):
    """Poll for result. Returns status: queued | running | complete | error."""
    result = job_store.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result
```

The frontend polls `GET /analyze-custom/{job_id}` every 2-5 seconds until `status == "complete"`. This is simpler to implement than WebSockets and perfectly adequate for a portfolio project where one user submits at a time.

### Why Not `ProcessPoolExecutor` for Qwen?

`ProcessPoolExecutor` would avoid the GIL for the CPU computation, but it requires the model to be serialized (pickled) between processes on each call — or re-loaded in each worker process (2-3GB RAM per worker). For a portfolio single-process server, the ThreadPoolExecutor + Semaphore(1) approach avoids blocking the event loop while keeping model memory in one process. The GIL is released during the C-extension code in PyTorch's forward pass anyway, so threads do achieve real concurrency for this workload.

---

## Section 3: TTL Cache Patterns for Financial Data

### Problems with the Current Cache

```python
cache: Dict[str, Any] = {"stock_data": None, "news": None}
```

This cache has two bugs:
1. No TTL — data is served stale forever once populated.
2. `if cache["stock_data"]:` evaluates to `False` when the dict is empty (`{}`) — meaning a valid but empty result will be re-fetched on every request.

### Recommended Library: `cachetools.TTLCache`

**Confidence: HIGH** — cachetools is the de-facto standard Python in-memory TTL cache. It is well-maintained (v7.0.5 as of early 2026), has zero dependencies, and provides thread-safe operation via a lock argument.

```python
from cachetools import TTLCache
import threading

# Stock price: 15-minute TTL (market moves slowly; yfinance daily bars don't change intraday)
# News: 5-minute TTL (news freshness matters more; API rate limits are a concern)
stock_cache = TTLCache(maxsize=10, ttl=900)   # 15 min
news_cache  = TTLCache(maxsize=50, ttl=300)   # 5 min

# cachetools is NOT thread-safe by default.
# FastAPI's thread pool runs sync endpoints in multiple threads,
# so a lock is required.
cache_lock = threading.Lock()
```

### TTL Recommendations for This Domain

| Data Type | Recommended TTL | Rationale |
|-----------|----------------|-----------|
| Stock price history (1y daily bars) | 900s (15 min) | Daily OHLC bars don't change intraday; yfinance 1y history is expensive to fetch |
| News + FinBERT sentiment (bulk) | 300s (5 min) | News freshness matters; Yahoo Finance search API is cheap |
| Custom Qwen analysis result | Cache by text hash, TTL 3600s | Deterministic for same input; expensive to recompute |
| Per-ticker news | 180s (3 min) | User explicitly requested fresh ticker data |

### Usage Pattern

```python
from cachetools import TTLCache, keys
import threading

stock_cache = TTLCache(maxsize=10, ttl=900)
news_cache  = TTLCache(maxsize=50, ttl=300)
cache_lock  = threading.Lock()


def get_cached_stock_data():
    with cache_lock:
        return stock_cache.get("all")


def set_cached_stock_data(data):
    with cache_lock:
        stock_cache["all"] = data


def get_cached_news(ticker: str | None):
    cache_key = ticker or "__all__"
    with cache_lock:
        return news_cache.get(cache_key)


def set_cached_news(ticker: str | None, data):
    cache_key = ticker or "__all__"
    with cache_lock:
        news_cache[cache_key] = data
```

And in the route handler, replace the current check:

```python
# Before (buggy):
if cache["stock_data"]:
    return cache["stock_data"]

# After (correct):
cached = get_cached_stock_data()
if cached is not None:  # Explicit None check, not falsy check
    return cached
```

### Async Alternative: `aiocache`

If all endpoints become `async def`, `aiocache` provides native async TTL caching with a decorator:

```python
from aiocache import cached
from aiocache.serializers import JsonSerializer

@cached(ttl=900, serializer=JsonSerializer())
async def fetch_all_stock_data():
    ...
```

`aiocache` supports Redis as a backend for multi-worker deployments. For this project's single-process scope, `cachetools` is simpler and has fewer moving parts.

---

## Section 4: Non-Blocking yfinance

### Why the Current Pattern Blocks

```python
@app.get("/stock-price")
def get_stock_price():   # sync def — FastAPI runs this in a thread pool, which is correct
    for ticker in selected_symbols:
        stock = yf.Ticker(ticker)
        hist_1y = stock.history(period='1y', interval='1d')  # one HTTP call per ticker, serial
```

The handler is `def` (not `async def`), which is actually correct — FastAPI runs sync handlers in a `ThreadPoolExecutor`, so they do not block the event loop. However:

1. The calls are **serial** — 15 tickers × ~1-2s each = 15-30s total per cache miss.
2. The news handler is also `def` but calls `requests.get()` — again serial across 5 symbols.

### The Fix: `asyncio.gather` + `loop.run_in_executor`

Convert the handlers to `async def` and fan out each ticker fetch concurrently:

```python
import asyncio
from functools import partial
from starlette.concurrency import run_in_threadpool


def _fetch_single_ticker(ticker: str) -> dict | None:
    """
    Pure sync function. Safe to call from a thread pool.
    Each call gets its own yf.Ticker instance — avoids the shared-global
    thread-safety bug in yf.download().
    """
    try:
        stock = yf.Ticker(ticker)
        hist_1y = stock.history(period="1y", interval="1d").reset_index()
        if hist_1y.empty:
            return None
        # ... transform as before ...
        return {ticker: {...}}
    except Exception as e:
        print(f"Error fetching {ticker}: {e}", flush=True)
        return None


@app.get("/stock-price")
async def get_stock_price():
    cached = get_cached_stock_data()
    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()

    # Fan out: all 15 (or 100) tickers run in threads concurrently
    tasks = [
        loop.run_in_executor(None, _fetch_single_ticker, ticker)
        for ticker in selected_symbols
    ]
    results = await asyncio.gather(*tasks)

    all_data = {}
    for result in results:
        if result:
            all_data.update(result)

    set_cached_stock_data(all_data)
    return all_data
```

Expected speedup: 15-30s serial becomes ~2-4s (bounded by the slowest single ticker fetch).

### yfinance Thread Safety: Critical Note

**Confidence: HIGH** — Verified against GitHub issue #2557 in the yfinance repository.

`yf.download()` uses module-level shared dictionaries (`_DFS`, `_ERRORS`) that are not protected by locks. Concurrent calls to `download()` for different parameters can silently overwrite each other's results.

**Safe pattern:** Use `yf.Ticker(ticker).history(...)` (per-instance API) rather than `yf.download()` in concurrent code. Each `Ticker` instance has its own state. This is what the current code already uses — keep using it, just fan it out concurrently.

### Scaling to 100 Tickers

For 100 tickers, a raw `gather` of 100 threads will hammer Yahoo Finance's rate limiter. Use a semaphore to cap concurrency:

```python
_yf_semaphore = asyncio.Semaphore(10)  # max 10 concurrent yfinance calls

async def _fetch_ticker_safe(ticker: str, loop) -> dict | None:
    async with _yf_semaphore:
        return await loop.run_in_executor(None, _fetch_single_ticker, ticker)

@app.get("/stock-price")
async def get_stock_price():
    cached = get_cached_stock_data()
    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()
    tasks = [_fetch_ticker_safe(t, loop) for t in selected_symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... process results
```

Yahoo Finance has informal rate limits around 10-20 requests/second per IP. A semaphore of 10 keeps you under the limit while still providing ~10x speedup over serial calls.

---

## Section 5: Rate Limiting and API Key Auth in FastAPI

### Rate Limiting: `slowapi`

`slowapi` is the de-facto rate limiting library for FastAPI/Starlette, adapted from `flask-limiter`. It is actively maintained and uses `limits` under the hood.

**Confidence: HIGH** — Verified against the official slowapi GitHub repository and multiple 2025-2026 tutorials.

```bash
pip install slowapi
```

```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

Apply per-endpoint limits. The `request: Request` parameter is **required** — slowapi will silently fail to apply limits if it is absent:

```python
@app.get("/stock-price")
@limiter.limit("30/minute")        # yfinance calls are expensive
async def get_stock_price(request: Request):
    ...

@app.get("/news")
@limiter.limit("60/minute")
async def get_news(request: Request, ticker: str = None):
    ...

@app.post("/analyze-custom")
@limiter.limit("5/minute")         # Qwen inference is slow; throttle hard
async def submit_analysis(request: Request, text: str):
    ...
```

Note that decorator order matters: `@app.get(...)` must come before `@limiter.limit(...)`.

### API Key Authentication

For a portfolio project, a simple `APIKeyHeader` dependency is sufficient. It integrates with FastAPI's OpenAPI schema (shows up in Swagger UI) and is composable with slowapi.

```python
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
VALID_API_KEY = os.getenv("API_KEY", "dev-key-change-me")


async def require_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
```

Apply globally via `app = FastAPI(dependencies=[Depends(require_api_key)])`, or per-route:

```python
@app.post("/analyze-custom", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def submit_analysis(request: Request, text: str):
    ...
```

If you want to keep `/stock-price` and `/news` public (portfolio demo), apply the dependency only to `/analyze-custom` to protect the expensive Qwen endpoint.

### Combined Pattern: Rate Limit by API Key

For a tiered approach (e.g., authenticated users get higher limits):

```python
def get_api_key_or_ip(request: Request) -> str:
    """Use API key as rate limit identifier if present, else fall back to IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == VALID_API_KEY:
        return f"key:{api_key}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_api_key_or_ip)
```

---

## Summary: What to Change in `main.py`

| Change | Priority | Effort |
|--------|----------|--------|
| Move model loads into `lifespan` | High | ~30 min |
| Convert `def` handlers to `async def` with `run_in_executor` | High | ~1 hour |
| Replace `cache` dict with `cachetools.TTLCache` + None-check | High | ~20 min |
| Add `asyncio.Semaphore(10)` for yfinance fan-out | Medium | ~20 min |
| Add `slowapi` rate limiting | Medium | ~30 min |
| Replace `/analyze-custom` with queue + polling | Medium | ~2 hours |
| Add `X-API-Key` header auth for `/analyze-custom` | Low | ~20 min |

Total estimated migration time: 5-6 hours for a brownfield refactor.

---

## Sources

- [FastAPI Lifespan Events (official docs)](https://fastapi.tiangolo.com/advanced/events/)
- [FastAPI Concurrency and async/await (official docs)](https://fastapi.tiangolo.com/async/)
- [run_in_executor vs run_in_threadpool — Sentry](https://sentry.io/answers/fastapi-difference-between-run-in-executor-and-run-in-threadpool/)
- [The Concurrency Mistake in FastAPI AI Services — JamWithAI](https://jamwithai.substack.com/p/the-concurrency-mistake-hiding-in)
- [Concurrency for Starlette/FastAPI Apps — Answer.AI](https://www.answer.ai/posts/2024-10-10-concurrency.html)
- [FastAPI BackgroundTasks vs ARQ — davidmuraya.com](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/)
- [ARQ vs Celery for FastAPI — bithost.in](https://www.bithost.in/blog/tech-3/how-to-run-fastapi-background-tasks-arq-vs-celery-11)
- [cachetools documentation — PyPI / readthedocs](https://pypi.org/project/cachetools/)
- [cachetools-async for asyncio — GitHub](https://github.com/imnotjames/cachetools-async)
- [yfinance thread safety issue #2557 — GitHub](https://github.com/ranaroussi/yfinance/issues/2557)
- [slowapi GitHub repository](https://github.com/laurentS/slowapi)
- [Using SlowAPI in FastAPI — Medium (Jan 2026)](https://shiladityamajumder.medium.com/using-slowapi-in-fastapi-mastering-rate-limiting-like-a-pro-19044cb6062b)
- [FastAPI API Key Authentication — itsjoshcampos.codes](https://itsjoshcampos.codes/fast-api-api-key-authorization)
- [Asyncio Semaphores for LLM Concurrency — newline.co](https://www.newline.co/@zaoyang/python-asyncio-for-llm-concurrency-best-practices--bc079176)
