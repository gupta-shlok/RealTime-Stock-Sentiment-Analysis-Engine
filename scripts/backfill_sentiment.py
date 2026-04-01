"""
Batch backfill script — collects the past week of news for all S&P 100 tickers,
scores each headline with FinBERT, and merges daily sentiment scores into
backend/data/sentiment_scores.json.

Usage (from repo root):
    python scripts/backfill_sentiment.py               # all tickers
    python scripts/backfill_sentiment.py AAPL MSFT     # subset

Run in background (Unix):
    python scripts/backfill_sentiment.py > backfill.log 2>&1 &

Run in background (Windows PowerShell):
    Start-Process python -ArgumentList "scripts/backfill_sentiment.py" -RedirectStandardOutput backfill.log -NoNewWindow
"""

import sys
import os
import json
import time
import tempfile
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── Path setup so we can import from backend ────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from tickers import TICKER_DATA, ALL_TICKERS

# ── Constants ────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(BACKEND_DIR, "data")
SCORES_FILE = os.path.join(DATA_DIR, "sentiment_scores.json")
FINBERT_MIN_CONFIDENCE = 0.55
LOOKBACK_DAYS = 7
DELAY_BETWEEN_TICKERS = 0.5   # seconds — be polite to Yahoo Finance

# ── Model (loaded once) ──────────────────────────────────────────────────────
_tokenizer = None
_model = None


def _load_model():
    global _tokenizer, _model
    if _tokenizer is not None:
        return
    print("Loading FinBERT model (ProsusAI/finbert)...", flush=True)
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    model_id = "ProsusAI/finbert"
    _tokenizer = AutoTokenizer.from_pretrained(model_id)
    _model = AutoModelForSequenceClassification.from_pretrained(model_id)
    _model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        _model = _model.cuda()
    print(f"FinBERT loaded on {device}.", flush=True)


def _finbert_score(text: str):
    """Returns (score, confidence). score = P(pos) - P(neg) in [-1, 1]."""
    import torch
    import torch.nn.functional as F
    try:
        inputs = _tokenizer(
            text[:512],
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(_model.device)
        with torch.no_grad():
            outputs = _model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]
        score = probs[0].item() - probs[1].item()
        confidence = probs.max().item()
        return score, confidence
    except Exception as e:
        print(f"  FinBERT error: {e}", flush=True)
        return 0.0, 0.0


# ── Persistence helpers ──────────────────────────────────────────────────────

def _load_scores() -> dict:
    try:
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_scores_atomic(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, SCORES_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── News fetching (yfinance gives more history than the search API) ───────────

def _fetch_news_yfinance(ticker: str, cutoff_ts: int) -> list:
    """Returns list of {title, date_str} dicts published on/after cutoff_ts."""
    import yfinance as yf
    articles = []
    try:
        news_items = yf.Ticker(ticker).news or []
        for item in news_items:
            pub_time = item.get("content", {}).get("pubDate") or item.get("providerPublishTime")
            if isinstance(pub_time, str):
                # ISO format e.g. "2026-03-28T14:23:00Z"
                try:
                    dt = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
                    ts = int(dt.timestamp())
                except ValueError:
                    continue
            elif isinstance(pub_time, (int, float)):
                ts = int(pub_time)
            else:
                continue
            if ts < cutoff_ts:
                continue
            title = (
                item.get("content", {}).get("title")
                or item.get("title")
                or ""
            )
            if not title:
                continue
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            articles.append({"title": title, "date_str": date_str})
    except Exception as e:
        print(f"  yfinance news error for {ticker}: {e}", flush=True)
    return articles


# ── Aggregation ──────────────────────────────────────────────────────────────

def _aggregate(articles_by_date: dict) -> dict:
    """articles_by_date: {date_str: [{"score": float, "confidence": float}]}
    Returns {date_str: daily_score} only for dates with enough confident articles."""
    result = {}
    for date_str, arts in articles_by_date.items():
        filtered = [
            (a["score"], a["confidence"])
            for a in arts
            if a.get("confidence", 0.0) >= FINBERT_MIN_CONFIDENCE
        ]
        if not filtered:
            continue
        numerator = sum(s * c for s, c in filtered)
        denominator = sum(c for _, c in filtered)
        result[date_str] = round(numerator / denominator, 4)
    return result


# ── Main backfill logic ──────────────────────────────────────────────────────

def backfill(tickers: list):
    _load_model()

    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    cutoff_ts = int(cutoff_dt.timestamp())
    cutoff_date = cutoff_dt.strftime("%Y-%m-%d")
    print(f"Backfilling {len(tickers)} tickers from {cutoff_date} onwards...", flush=True)

    scores = _load_scores()
    updated = 0

    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker}", end=" ", flush=True)
        articles = _fetch_news_yfinance(ticker, cutoff_ts)
        if not articles:
            print("  no articles", flush=True)
            time.sleep(DELAY_BETWEEN_TICKERS)
            continue

        # Score each headline
        by_date = defaultdict(list)
        for art in articles:
            score, conf = _finbert_score(art["title"])
            by_date[art["date_str"]].append({"score": score, "confidence": conf})

        daily = _aggregate(by_date)
        if not daily:
            print(f"  {len(articles)} articles, 0 passed confidence filter", flush=True)
            time.sleep(DELAY_BETWEEN_TICKERS)
            continue

        # Merge into existing scores (don't overwrite newer data for the same date)
        if ticker not in scores:
            scores[ticker] = {}
        scores[ticker].update(daily)
        print(f"  {len(articles)} articles -> {len(daily)} date(s): {sorted(daily.keys())}", flush=True)
        updated += 1
        time.sleep(DELAY_BETWEEN_TICKERS)

    # Prune entries older than 35 days before writing
    prune_cutoff = (datetime.now(timezone.utc).date() - timedelta(days=35)).isoformat()
    for ticker in list(scores.keys()):
        scores[ticker] = {d: v for d, v in scores[ticker].items() if d >= prune_cutoff}
        if not scores[ticker]:
            del scores[ticker]

    _write_scores_atomic(scores)
    print(f"\nDone. {updated}/{len(tickers)} tickers updated. Scores written to:\n  {SCORES_FILE}", flush=True)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill 7-day sentiment scores")
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Specific tickers to backfill (default: all S&P 100 tickers)",
    )
    args = parser.parse_args()

    target_tickers = args.tickers if args.tickers else sorted(ALL_TICKERS)
    backfill(target_tickers)
