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
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from config import get_settings, Settings
from contextlib import asynccontextmanager
from cachetools import TTLCache

# Set a global timeout for network requests
socket.setdefaulttimeout(10)

# Model placeholders (set in lifespan)
finbert_pipe = None
qwen_tokenizer = None
qwen_model = None

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global finbert_pipe, qwen_tokenizer, qwen_model
    # Load FinBERT
    device = "cuda" if torch.cuda.is_available() else "cpu"
    finbert_pipe = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=0 if device == "cuda" else -1)
    app.state.finbert_pipe = finbert_pipe
    # Warm-up FinBERT
    finbert_pipe("Warm-up sentence.")

    # Load Qwen2.5-1.5B-Instruct
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
    # Start background worker for Qwen jobs
    asyncio.create_task(qwen_worker())
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
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key

# Constants
selected_symbols = ['AAPL', 'AMZN', 'AMD', 'BA', 'BX', 'COST', 'CRM', 'DIS', 'GOOG', 'GS', 'IBM', 'INTC', 'MS', 'NKE', 'NVDA']

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


def finbert_score(text: str) -> float:
    """Run FinBERT and return a signed score in [-1, 1]."""
    try:
        result = finbert_pipe(text[:512])[0]
        label = result['label']
        score = result['score']
        if label == 'positive':
            return score
        elif label == 'negative':
            return -score
        return 0.0
    except Exception as e:
        print(f"FinBERT error: {e}", flush=True)
        return 0.0


def analyze_sentiment_ensemble(text: str) -> float:
    """Quick ensemble score for bulk news tagging (FinBERT only for speed)."""
    return finbert_score(text)


def label_from_score(score: float) -> str:
    if score > 0.15:
        return "Bullish"
    elif score < -0.15:
        return "Bearish"
    return "Neutral"


# Background worker for Qwen job queue
async def qwen_worker():
    while True:
        job = await qwen_job_queue.get()
        job_id = job["job_id"]
        text = job["text"]
        try:
            # Run FinBERT scoring (synchronous, fast)
            fb_val = finbert_score(text)
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

    # Helper function to fetch data for a single ticker (runs in thread)
    def fetch_ticker_data(ticker: str) -> dict:
        try:
            stock = yf.Ticker(ticker)
            hist_1y = stock.history(period='1y', interval='1d').reset_index()
            if hist_1y.empty:
                return None
            latest_data = hist_1y.tail(2)
            if len(latest_data) >= 2:
                current_close = latest_data['Close'].iloc[-1]
                previous_close = latest_data['Close'].iloc[-2]
            else:
                current_close = hist_1y['Close'].iloc[-1]
                previous_close = current_close
            percent_change = (((current_close - previous_close) / previous_close) * 100) if previous_close != 0 else 0
            hist_1y['Month'] = hist_1y['Date'].dt.to_period('M')
            monthly_data = hist_1y.groupby('Month').agg({
                'Open': 'first',
                'Close': 'last',
                'High': 'max',
                'Low': 'min',
            }).reset_index()
            monthly_data['Month'] = monthly_data['Month'].dt.strftime('%Y-%m')
            return {
                "current_close": float(current_close),
                "previous_close": float(previous_close),
                "percent_change": float(percent_change),
                "history": monthly_data.to_dict(orient='records')
            }
        except Exception as e:
            print(f"Error fetching stock data for {ticker}: {e}", flush=True)
            return None

    # Concurrent fetch with semaphore limit (max 10 concurrent)
    semaphore = asyncio.Semaphore(10)
    async def bounded_fetch(ticker: str):
        async with semaphore:
            return await asyncio.to_thread(fetch_ticker_data, ticker)

    tasks = [bounded_fetch(t) for t in selected_symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_data = {}
    for ticker, result in zip(selected_symbols, results):
        if isinstance(result, Exception):
            print(f"Error fetching {ticker}: {result}", flush=True)
        elif result:  # not None and not empty
            all_data[ticker] = result

    stock_cache["stock_data"] = all_data
    return all_data


@app.get("/news")
def get_news(ticker: str = None):
    if not ticker and "news" in news_cache:
        return news_cache["news"]

    all_news = []
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    search_symbols = [ticker] if ticker else selected_symbols[:5]

    for symbol in search_symbols:
        try:
            print(f"Fetching Filtered Yahoo News for {symbol}...", flush=True)
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            news_items = data.get("news", [])
            for item in news_items:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
