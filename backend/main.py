from fastapi import FastAPI, Security, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from typing import Dict, Any
import yfinance as yf
from datetime import datetime
import requests
import json
import re
import os
import socket
import asyncio
import uuid
from asyncio import Queue
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
from config import get_settings, Settings
from contextlib import asynccontextmanager
from cachetools import TTLCache
import pandas as pd
from tickers import TICKER_DATA, ALL_TICKERS, SECTOR_TICKERS

# Tier 2 rotation offset for aggregated news feed
TIER2_OFFSET = 0

# Set a global timeout for network requests
socket.setdefaulttimeout(10)

# Model placeholders (set in lifespan)
# finbert_pipe removed — using AutoModelForSequenceClassification directly (D-03)
qwen_tokenizer = None
qwen_model = None

# ─── FinBERT scoring (SENT-01) ──────────────────────────────────────────────

def _finbert_infer(text: str):
    """Synchronous FinBERT forward pass. Run via asyncio.to_thread()."""
    inputs = app.state.finbert_tokenizer(
        text[:512],
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(app.state.finbert_model.device)
    with torch.no_grad():
        outputs = app.state.finbert_model(**inputs)
    probs = F.softmax(outputs.logits, dim=-1)[0]
    # id2label from ProsusAI/finbert config.json: {0: positive, 1: negative, 2: neutral}
    score = probs[0].item() - probs[1].item()
    confidence = probs.max().item()
    return score, confidence


def finbert_score(text: str) -> tuple:
    """
    Run FinBERT full-probability scoring (SENT-01, D-01, D-02).
    Returns (score, confidence):
      score      = P(positive) - P(negative)  in [-1, 1]
      confidence = max(softmax(logits))        in [0, 1]

    NOTE: Returns a TUPLE. All callers must unpack:
      score, conf = finbert_score(text)   <- correct
      score = finbert_score(text)[0]      <- also correct
      score = finbert_score(text)         <- WRONG -- will break
    """
    try:
        score, confidence = _finbert_infer(text)
        return score, confidence
    except Exception as e:
        print(f"FinBERT error: {e}", flush=True)
        return 0.0, 0.0


def analyze_sentiment_ensemble(text: str) -> float:
    """Quick ensemble score for bulk news tagging (FinBERT only for speed).
    Returns bare float for /news endpoint display (D-06: threshold doesn't affect display).
    """
    score, _ = finbert_score(text)
    return score


# ─── Confidence-weighted aggregation (SENT-02) ──────────────────────────────

def aggregate_daily_score(articles: list) -> float:
    """
    Compute confidence-weighted mean of article scores (SENT-02).
    Filters out articles where confidence < FINBERT_MIN_CONFIDENCE (D-04, D-05).
    Returns None if no articles pass the threshold (day is skipped in persistence).

    articles: list of {"score": float, "confidence": float}
    """
    settings = get_settings()
    threshold = settings.finbert_min_confidence  # default 0.55
    filtered = [
        (a["score"], a["confidence"])
        for a in articles
        if a.get("confidence", 0.0) >= threshold
    ]
    if not filtered:
        return None
    numerator = sum(s * c for s, c in filtered)
    denominator = sum(c for _, c in filtered)
    return numerator / denominator


# ─── Persistence helpers ─────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SCORES_FILE = os.path.join(DATA_DIR, "sentiment_scores.json")
NARRATIVES_FILE = os.path.join(DATA_DIR, "narratives.json")


def _load_scores_file() -> dict:
    """Load sentiment_scores.json; returns {} if missing or corrupt."""
    try:
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if not isinstance(e, FileNotFoundError):
            print(f"Warning: sentiment_scores.json corrupt, using empty dict: {e}", flush=True)
        return {}


def _load_narratives_file() -> dict:
    """Load narratives.json; returns {} if missing or corrupt."""
    try:
        with open(NARRATIVES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if not isinstance(e, FileNotFoundError):
            print(f"Warning: narratives.json corrupt, using empty dict: {e}", flush=True)
        return {}


def _write_json_atomic(path: str, data: dict):
    """Atomic JSON write using os.replace() (safe on Windows and Linux, D-10)."""
    import tempfile
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ─── Background scoring task (D-08, D-09, D-10) ─────────────────────────────

def _run_scoring_cycle():
    """
    Synchronous scoring cycle — called from asyncio.to_thread().
    Reads news_cache["news"], scores articles, writes sentiment_scores.json.
    Format: { "AAPL": { "2026-03-28": 0.34, ... }, ... }
    Prunes entries older than 35 days on each write (D-09).
    """
    from datetime import timezone, timedelta
    from collections import defaultdict

    cached_news = news_cache.get("news", [])
    if not cached_news:
        return

    # Group articles by (ticker, date)
    # Expected news item shape from /news endpoint:
    # {"ticker": "AAPL", "publishTime": "2026-03-28 10:30:00", "title": "...", ...}
    ticker_date_articles = defaultdict(lambda: defaultdict(list))

    for article in cached_news:
        ticker = article.get("ticker")
        if not ticker:
            continue
        publish_time = article.get("publishTime", "")
        try:
            date_str = publish_time[:10]  # "2026-03-28"
            datetime.strptime(date_str, "%Y-%m-%d")  # validate format
        except (ValueError, TypeError):
            continue
        title = article.get("title", "")
        if not title:
            continue
        score, confidence = finbert_score(title)
        ticker_date_articles[ticker][date_str].append({
            "score": score,
            "confidence": confidence,
        })

    # Compute daily scores
    new_scores = _load_scores_file()  # load existing (preserve history across cycles)
    for ticker, date_articles in ticker_date_articles.items():
        if ticker not in new_scores:
            new_scores[ticker] = {}
        for date_str, articles in date_articles.items():
            daily = aggregate_daily_score(articles)
            if daily is not None:
                new_scores[ticker][date_str] = round(daily, 4)

    # Prune entries older than 35 days (D-09)
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=35)).isoformat()
    for ticker in list(new_scores.keys()):
        new_scores[ticker] = {
            d: v for d, v in new_scores[ticker].items() if d >= cutoff
        }
        if not new_scores[ticker]:
            del new_scores[ticker]

    _write_json_atomic(SCORES_FILE, new_scores)
    print(f"Scoring cycle complete: {len(new_scores)} tickers updated.", flush=True)


async def sentiment_scoring_task():
    """
    Background task: runs every 5 minutes, writes sentiment_scores.json (D-08).
    Started via asyncio.create_task() in lifespan, 10s after startup.
    """
    await asyncio.sleep(10)  # Allow model warm-up to complete first
    while True:
        try:
            await asyncio.to_thread(_run_scoring_cycle)
        except Exception as e:
            print(f"Sentiment scoring task error: {e}", flush=True)
        await asyncio.sleep(300)  # 5 minutes


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global qwen_tokenizer, qwen_model
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load FinBERT — AutoModelForSequenceClassification (replaces pipeline, D-01, D-03)
    FINBERT_MODEL_ID = "ProsusAI/finbert"
    finbert_tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL_ID)
    finbert_model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL_ID)
    finbert_model.eval()
    if device == "cuda":
        finbert_model = finbert_model.cuda()
    app.state.finbert_tokenizer = finbert_tokenizer
    app.state.finbert_model = finbert_model

    # Warm-up FinBERT (eliminates first-request latency spike)
    _warmup_score, _ = finbert_score("Warm-up sentence for FinBERT.")
    print(f"FinBERT loaded. Warm-up score: {_warmup_score:.3f}", flush=True)

    # Load Qwen2.5-1.5B-Instruct (unchanged from Phase 2)
    QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
    qwen_tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_ID)
    qwen_model = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto",
    )
    app.state.qwen_tokenizer = qwen_tokenizer
    app.state.qwen_model = qwen_model

    # Warm-up Qwen (single generate call with dummy input)
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze: Stock market is stable."}
    ]
    text_input = qwen_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = qwen_tokenizer(text_input, return_tensors="pt").to(qwen_model.device)
    with torch.no_grad():
        _ = qwen_model.generate(
            **inputs,
            max_new_tokens=20,
            temperature=0.1,
            do_sample=False,
            pad_token_id=qwen_tokenizer.eos_token_id
        )
    print("Models loaded and warmed up.", flush=True)

    # Start background workers
    asyncio.create_task(qwen_worker())
    asyncio.create_task(sentiment_scoring_task())  # D-08: 5-minute background scorer

    yield

app = FastAPI(lifespan=lifespan)

# Async job queue for Qwen inference (non-blocking /analyze-custom)
qwen_job_queue = Queue()
qwen_job_results: Dict[str, dict] = {}

# CORS — restricted to explicit origin list; wildcard + credentials is a browser security violation
_settings = get_settings()
_allowed_origins = [o.strip() for o in _settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# API key security dependency
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    api_key: str = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    # Allow bypass if api_key is set to default dev value (free local mode)
    if settings.api_key == "dev-key-optional":
        return "dev-key-optional"
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key

# Constants

def get_qwen_analysis(text: str) -> tuple:
    """Use Qwen2.5-1.5B to assess sentiment and provide concise reasoning."""
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a financial analyst. Respond ONLY with a JSON object, no extra text."
            },
            {
                "role": "user",
                "content": (
                    f"Analyze the sentiment of this financial news for investors. "
                    f"Reply with ONLY this JSON: "
                    f'{{\"sentiment\": \"bullish\"|\"bearish\"|\"neutral\", \"confidence\": 0.0-1.0, \"reason\": \"one concise sentence\"}}\n\n'
                    f"News: {text[:400]}"
                )
            }
        ]
        text_input = qwen_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = qwen_tokenizer(text_input, return_tensors="pt").to(qwen_model.device)
        with torch.no_grad():
            outputs = qwen_model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.1,
                do_sample=False,
                pad_token_id=qwen_tokenizer.eos_token_id
            )
        response = qwen_tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True
        ).strip()

        # Extract JSON from response
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            sentiment = data.get("sentiment", "neutral").lower()
            confidence = float(data.get("confidence", 0.5))
            reason = data.get("reason", response)
            if sentiment == "bullish":
                score = confidence
            elif sentiment == "bearish":
                score = -confidence
            else:
                score = 0.0
            return score, reason
        return 0.0, response
    except Exception as e:
        print(f"Qwen error: {e}", flush=True)
        return 0.0, "Reasoning unavailable."


def label_from_score(score: float) -> str:
    if score > 0.15:
        return "Bullish"
    elif score < -0.15:
        return "Bearish"
    return "Neutral"


# ─── Narrative helpers (SENT-05) ─────────────────────────────────────────────

def build_narrative_prompt(ticker: str, headlines: list) -> str:
    """
    Build the Qwen prompt for narrative generation (SENT-05).
    headlines: [{"title": str, "score": float}, ...]  top 8 most recent
    """
    headline_block = "\n".join(
        f"{i+1}. [{'+'if h['score'] > 0 else ''}{h['score']:.2f}] {h['title']}"
        for i, h in enumerate(headlines[:8])
    )
    return (
        f"You are a concise financial analyst. Below are the 8 most recent news headlines "
        f"for {ticker} with their FinBERT sentiment scores (positive=+, negative=-).\n\n"
        f"{headline_block}\n\n"
        f"Write a 2-3 sentence summary explaining what is currently driving {ticker}'s sentiment. "
        f"Reference specific headlines by number and cite their sentiment signals (positive/negative score). "
        f"Do not use generic phrases like 'the stock is moving' or 'investors are watching'. Be specific."
    )


def _get_ticker_headlines(ticker: str) -> list:
    """
    Retrieve top 8 recent headlines for a ticker from the news cache.
    Returns list of {"title": str, "score": float} sorted by publishTime descending.
    Scores are computed via finbert_score() for each headline title.
    """
    cached_news = news_cache.get("news", [])
    ticker_articles = [a for a in cached_news if a.get("ticker") == ticker and a.get("title")]
    # Sort by publishTime descending (ISO-like string "YYYY-MM-DD HH:MM:SS" sorts correctly)
    ticker_articles.sort(key=lambda a: a.get("publishTime", ""), reverse=True)
    result = []
    for article in ticker_articles[:8]:
        score, _ = finbert_score(article["title"])
        result.append({"title": article["title"], "score": round(score, 4)})
    return result


def get_qwen_narrative(ticker: str) -> str:
    """
    Synchronous: generate Qwen narrative for ticker.
    Called from qwen_worker() via asyncio.to_thread().
    Returns the narrative text string.
    """
    headlines = _get_ticker_headlines(ticker)
    if not headlines:
        return f"Insufficient news data available for {ticker} to generate a narrative."

    prompt = build_narrative_prompt(ticker, headlines)
    messages = [
        {"role": "system", "content": "You are a concise financial analyst. Answer in 2-3 sentences only."},
        {"role": "user", "content": prompt},
    ]
    text_input = qwen_tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = qwen_tokenizer(text_input, return_tensors="pt").to(qwen_model.device)
    with torch.no_grad():
        outputs = qwen_model.generate(
            **inputs,
            max_new_tokens=250,
            temperature=0.3,
            do_sample=True,
            pad_token_id=qwen_tokenizer.eos_token_id,
        )
    narrative = qwen_tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    ).strip()
    return narrative


# Background worker for Qwen job queue
async def qwen_worker():
    while True:
        job = await qwen_job_queue.get()
        job_id = job["job_id"]
        job_type = job.get("type", "analyze")  # default is original analyze-custom behavior

        try:
            if job_type == "narrative":
                # SENT-05: Generate "why is this stock moving" narrative
                ticker = job["ticker"]
                narrative_text = await asyncio.to_thread(get_qwen_narrative, ticker)

                # Write to narratives.json (D-11, D-13)
                from datetime import timezone
                narratives = _load_narratives_file()
                narratives[ticker] = {
                    "narrative": narrative_text,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "headlines_used": min(8, len(_get_ticker_headlines(ticker))),
                }
                _write_json_atomic(NARRATIVES_FILE, narratives)

                qwen_job_results[job_id] = {
                    "status": "complete",
                    "ticker": ticker,
                    "narrative": narrative_text,
                }

            else:
                # Original analyze-custom behavior (unchanged from Phase 2)
                text = job["text"]
                fb_val, _ = finbert_score(text)  # unpack (score, confidence) tuple
                # Run Qwen analysis in a thread to avoid blocking event loop
                qwen_val, reason = await asyncio.to_thread(get_qwen_analysis, text)
                # Blend scores: 60% FinBERT + 40% Qwen
                blended_score = 0.6 * fb_val + 0.4 * qwen_val
                qwen_job_results[job_id] = {
                    "status": "complete",
                    "score": round(blended_score, 4),
                    "label": label_from_score(blended_score),
                    "finbert_score": round(fb_val, 4),
                    "llm_score": round(qwen_val, 4),
                    "reasoning": reason,
                    "model": "FinBERT + Qwen2.5-1.5B-Instruct"
                }

        except Exception as e:
            qwen_job_results[job_id] = {"status": "error", "error": str(e)}
        finally:
            qwen_job_queue.task_done()


# TTL cache (in-memory)
stock_cache = TTLCache(maxsize=1, ttl=900)   # 15 minutes
news_cache = TTLCache(maxsize=1, ttl=300)    # 5 minutes


def clean_time(news):
    for item in news:
        timestamp = item.get('providerPublishTime')
        if timestamp:
            datetime_object = datetime.fromtimestamp(timestamp)
            item['publishTime'] = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
    return news


@app.get("/stock-price")
async def get_stock_price():
    if "stock_data" in stock_cache:
        return stock_cache["stock_data"]

    symbols = ALL_TICKERS
    # Split into two batches of 50 each (for 102 tickers => 50 + 52)
    if len(symbols) > 50:
        batches = [symbols[:50], symbols[50:]]
    else:
        batches = [symbols]

    all_data = {}  # ticker -> data

    for i, batch in enumerate(batches):
        if not batch:
            continue
        try:
            batch_df = yf.download(batch, period='1y', interval='1d', threads=False)
        except Exception as e:
            print(f"Error downloading batch for {len(batch)} tickers: {e}", flush=True)
            continue

        for ticker in batch:
            try:
                # Extract ticker-specific DataFrame from batch
                if isinstance(batch_df.columns, pd.MultiIndex):
                    # Determine which level contains ticker symbols (yfinance may use either orientation)
                    level0_vals = batch_df.columns.get_level_values(0).unique()
                    level1_vals = batch_df.columns.get_level_values(1).unique()
                    if ticker in level0_vals:
                        ticker_df = batch_df.xs(ticker, axis=1, level=0)
                    elif ticker in level1_vals:
                        ticker_df = batch_df.xs(ticker, axis=1, level=1)
                    else:
                        # Ticker not found in either level, skip
                        continue
                else:
                    ticker_df = batch_df  # single ticker batch

                if ticker_df.empty:
                    continue
                if 'Close' not in ticker_df.columns:
                    continue

                close_series = ticker_df['Close']
                if len(close_series) >= 2:
                    current_close = close_series.iloc[-1]
                    previous_close = close_series.iloc[-2]
                else:
                    current_close = close_series.iloc[-1]
                    previous_close = current_close
                percent_change = ((current_close - previous_close) / previous_close * 100) if previous_close != 0 else 0.0

                # Monthly aggregation: group by month from DatetimeIndex
                if not isinstance(ticker_df.index, pd.DatetimeIndex):
                    # Skip if index is not datetime
                    history = []
                else:
                    ticker_df['Month'] = ticker_df.index.to_period('M')
                    monthly_agg = ticker_df.groupby('Month').agg({
                        'Open': 'first',
                        'Close': 'last',
                        'High': 'max',
                        'Low': 'min'
                    })
                    monthly_agg = monthly_agg.reset_index()
                    monthly_agg['Month'] = monthly_agg['Month'].dt.strftime('%Y-%m')
                    history = monthly_agg.to_dict(orient='records')

                all_data[ticker] = {
                    "current_close": float(current_close),
                    "previous_close": float(previous_close),
                    "percent_change": float(percent_change),
                    "history": history
                }
            except Exception as e:
                print(f"Error processing {ticker} in batch: {e}", flush=True)
                continue

        # Polite delay between batches (1.5s) except after last batch
        if i < len(batches) - 1:
            await asyncio.sleep(1.5)

    # Reorganize data by GICS sector
    sector_data = {}
    for ticker, data in all_data.items():
        sector = TICKER_DATA.get(ticker, {}).get('sector', 'Unknown')
        sector_data.setdefault(sector, {})[ticker] = data

    stock_cache["stock_data"] = sector_data
    return sector_data


@app.get("/news")
def get_news(ticker: str = None):
    global TIER2_OFFSET
    if not ticker and "news" in news_cache:
        return news_cache["news"]

    all_news = []
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    # Determine ticker list based on tiering or single-ticker request
    if ticker:
        search_symbols = [ticker]
        tier2_pool_len = 0  # not used for single ticker
    else:
        # Build tiered selection: Tier1 (top 20 by market cap) + rotating Tier2 slice (40 tickers from next 60)
        pairs = []
        for t in ALL_TICKERS:
            data = TICKER_DATA.get(t, {})
            mc = data.get('market_cap', 0)
            if mc and mc > 0:
                pairs.append((t, mc))
        # Sort descending by market cap
        sorted_tickers = [t for t, _ in sorted(pairs, key=lambda x: x[1], reverse=True)]
        tier1 = sorted_tickers[:20]
        tier2_pool = sorted_tickers[20:60]
        tier3 = sorted_tickers[60:]  # excluded from aggregated feed
        # Compute rotating Tier2 selection
        n = len(tier2_pool)
        if n > 0:
            start = TIER2_OFFSET % n
            tier2 = [tier2_pool[(start + i) % n] for i in range(min(40, n))]
        else:
            tier2 = []
        search_symbols = tier1 + tier2
        tier2_pool_len = n
        print(f"Tiered news: Tier1={len(tier1)}, Tier2={len(tier2)} (offset={TIER2_OFFSET}), Tier3={len(tier3)}", flush=True)

    seen_uuids = set()

    for symbol in search_symbols:
        try:
            print(f"Fetching Filtered Yahoo News for {symbol}...", flush=True)
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            news_items = data.get("news", [])
            for item in news_items:
                # Deduplication: skip if UUID already seen
                uuid = item.get('uuid')
                if uuid and uuid in seen_uuids:
                    continue
                if uuid:
                    seen_uuids.add(uuid)

                finance_info = item.get("finance", {})
                premium_config = finance_info.get("premiumFinance", {})
                is_premium = premium_config.get("isPremiumNews", False)

                if not is_premium:
                    title = item.get("title", "")
                    fb_val = analyze_sentiment_ensemble(title)
                    item['sentiment_score'] = float(fb_val)
                    item['sentiment_label'] = label_from_score(fb_val)
                    all_news.append(item)

            print(f"Success for {symbol}", flush=True)
        except Exception as e:
            print(f"Error fetching filtered news for {symbol}: {e}", flush=True)

    news_sorted = sorted(all_news, key=lambda x: x.get('providerPublishTime', 0), reverse=True)
    latest_articles = news_sorted[:20]

    if not ticker:
        news_cache["news"] = latest_articles
        # Rotate TIER2_OFFSET for next aggregated call
        if tier2_pool_len > 0:
            TIER2_OFFSET = (TIER2_OFFSET + 40) % tier2_pool_len

    return latest_articles


@app.get("/analyze-custom")
async def analyze_custom(
    text: str = Query(..., min_length=1, max_length=2000, description="Financial text to analyze (max 2000 chars)"),
    api_key: str = Security(require_api_key),
):
    """Deep-dive analysis blending FinBERT precision with Qwen2.5 reasoning (non-blocking)."""
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    # Initialize pending status
    qwen_job_results[job_id] = {"status": "pending"}
    # Enqueue the job for background processing
    await qwen_job_queue.put({"job_id": job_id, "text": text})
    # Return job ID immediately
    return {"job_id": job_id, "status": "pending"}


@app.get("/analyze-custom/{job_id}")
async def get_analyze_custom_status(job_id: str):
    result = qwen_job_results.get(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


# ─── Sentiment trends endpoint (SENT-03) ─────────────────────────────────────

WINDOW_TO_SPAN = {"7d": 5, "30d": 20}


@app.get("/sentiment-trends")
async def get_sentiment_trends(
    ticker: str,
    window: str = "7d",
    _key: str = Depends(require_api_key),
):
    """
    Returns EMA-smoothed sentiment time series for a ticker.
    window: '7d' (span=5) or '30d' (span=20).
    Data sourced from sentiment_scores.json written by sentiment_scoring_task.
    """
    span = WINDOW_TO_SPAN.get(window)
    if span is None:
        raise HTTPException(
            status_code=400,
            detail="window must be '7d' or '30d'",
        )

    scores = _load_scores_file().get(ticker, {})
    if not scores:
        return {"ticker": ticker, "window": window, "data": []}

    series = pd.Series(scores).sort_index()  # ISO date strings sort lexicographically = chronologically
    ema = series.ewm(span=span).mean()
    return {
        "ticker": ticker,
        "window": window,
        "data": [{"date": d, "score": round(float(v), 4)} for d, v in ema.items()],
    }


# ─── Sector sentiment endpoint (SENT-04) ─────────────────────────────────────

@app.get("/sector-sentiment")
async def get_sector_sentiment(_key: str = Depends(require_api_key)):
    """
    Returns equal-weight sector averages from the most recent daily score per constituent.
    Excludes sectors with fewer than 3 constituent stocks in the data (stock_count >= 3 rule).
    Real Estate (2 tickers) is always excluded.
    Energy (3) and Utilities (3) are included when data is available.
    """
    all_scores = _load_scores_file()
    result = {}

    for sector, tickers_in_sector in SECTOR_TICKERS.items():
        sector_scores = []
        for t in tickers_in_sector:
            ticker_dates = all_scores.get(t, {})
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


# ─── Stock narrative endpoint (SENT-05) ──────────────────────────────────────

@app.get("/stock-narrative/{ticker}")
async def get_stock_narrative(
    ticker: str,
    _key: str = Depends(require_api_key),
):
    """
    Returns a Qwen-generated narrative explaining the ticker's current sentiment.
    Cache freshness: 1 hour (D-12). Format per D-13:
      {"status": "complete", "ticker": "AAPL", "narrative": "...", "generated_at": "...", "headlines_used": 8}
    If stale or missing:
      {"status": "pending", "job_id": "<uuid>"}  — poll qwen_job_results[job_id]
    """
    from datetime import timezone

    narratives = _load_narratives_file()
    entry = narratives.get(ticker)

    if entry:
        try:
            generated_at = datetime.fromisoformat(entry["generated_at"])
            # Ensure timezone-aware comparison
            if generated_at.tzinfo is None:
                from datetime import timezone as tz
                generated_at = generated_at.replace(tzinfo=tz.utc)
            age_seconds = (datetime.now(timezone.utc) - generated_at).total_seconds()
            if age_seconds < 3600:  # less than 1 hour old — serve from cache
                return {"status": "complete", "ticker": ticker, **entry}
        except (ValueError, KeyError):
            pass  # corrupt entry — fall through to enqueue

    # Stale or missing — enqueue Qwen narrative job (same pattern as /analyze-custom)
    job_id = str(uuid.uuid4())
    qwen_job_results[job_id] = {"status": "pending"}
    await qwen_job_queue.put({
        "job_id": job_id,
        "type": "narrative",
        "ticker": ticker,
    })
    return {"status": "pending", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
