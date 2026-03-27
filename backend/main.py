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
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from config import get_settings, Settings

# Set a global timeout for network requests
socket.setdefaulttimeout(10)

app = FastAPI()

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

# --- Ensemble Sentiment Initialization ---
print("Initializing Sentiment Ensemble...", flush=True)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

# 1. FinBERT — Financial domain specialist (fast, precise, tiny model)
finbert_pipe = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert",
    device=0 if device == "cuda" else -1
)
print("FinBERT loaded.", flush=True)

# 2. Qwen2.5-1.5B-Instruct — Lightweight LLM for reasoning
# Runs efficiently on CPU (32GB RAM) or CUDA if available
QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
qwen_tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_ID)
qwen_model = AutoModelForCausalLM.from_pretrained(
    QWEN_MODEL_ID,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto",
)
print("Qwen2.5-1.5B-Instruct loaded.", flush=True)
print("Ensemble ready!", flush=True)


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


# In-memory cache
cache: Dict[str, Any] = {
    "stock_data": None,
    "news": None
}


def clean_time(news):
    for item in news:
        timestamp = item.get('providerPublishTime')
        if timestamp:
            datetime_object = datetime.fromtimestamp(timestamp)
            item['publishTime'] = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
    return news


@app.get("/stock-price")
def get_stock_price():
    if cache["stock_data"]:
        return cache["stock_data"]

    all_data = {}
    for ticker in selected_symbols:
        try:
            stock = yf.Ticker(ticker)
            hist_1y = stock.history(period='1y', interval='1d').reset_index()

            if hist_1y.empty:
                continue

            latest_data = hist_1y.tail(2)
            if len(latest_data) >= 2:
                current_close = latest_data['Close'].iloc[-1]
                previous_close = latest_data['Close'].iloc[-2]
            else:
                current_close = hist_1y['Close'].iloc[-1]
                previous_close = current_close

            percent_change = (
                ((current_close - previous_close) / previous_close) * 100
                if previous_close != 0 else 0
            )

            hist_1y['Month'] = hist_1y['Date'].dt.to_period('M')
            monthly_data = hist_1y.groupby('Month').agg({
                'Open': 'first',
                'Close': 'last',
                'High': 'max',
                'Low': 'min',
            }).reset_index()
            monthly_data['Month'] = monthly_data['Month'].dt.strftime('%Y-%m')

            all_data[ticker] = {
                "current_close": float(current_close),
                "previous_close": float(previous_close),
                "percent_change": float(percent_change),
                "history": monthly_data.to_dict(orient='records')
            }
        except Exception as e:
            print(f"Error fetching stock data for {ticker}: {e}", flush=True)

    cache["stock_data"] = all_data
    return all_data


@app.get("/news")
def get_news(ticker: str = None):
    if not ticker and cache["news"]:
        return cache["news"]

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
        cache["news"] = latest_articles

    return latest_articles


@app.get("/analyze-custom")
def analyze_custom(
    text: str = Query(..., min_length=1, max_length=2000, description="Financial text to analyze (max 2000 chars)"),
    api_key: str = Security(require_api_key),
):
    """Deep-dive analysis blending FinBERT precision with Qwen2.5 reasoning."""
    try:
        # FinBERT for precise financial sentiment scoring
        fb_val = finbert_score(text)

        # Qwen2.5 for reasoning and narrative understanding
        qwen_val, reasoning = get_qwen_analysis(text)

        # Blend: 60% FinBERT (domain expert) + 40% Qwen (contextual reasoning)
        blended_score = 0.6 * fb_val + 0.4 * qwen_val

        return {
            "score": round(blended_score, 4),
            "label": label_from_score(blended_score),
            "finbert_score": round(fb_val, 4),
            "llm_score": round(qwen_val, 4),
            "reasoning": reasoning,
            "model": "FinBERT + Qwen2.5-1.5B-Instruct Ensemble"
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
