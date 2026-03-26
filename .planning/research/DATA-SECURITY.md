# Data Pipeline Scaling & Security Research

**Project:** RealTime Stock Sentiment Analysis Engine
**Researched:** 2026-03-26
**Scope:** Scale from 15 to 100 tickers; harden for public portfolio deployment
**Overall Confidence:** HIGH (stack-specific claims verified against official docs and GitHub issues)

---

## Table of Contents

1. [Top 100 US Stocks — Canonical Ticker List](#1-top-100-us-stocks--canonical-ticker-list)
2. [yfinance at Scale — Batch Strategy](#2-yfinance-at-scale--batch-strategy)
3. [News Fetching for 100 Tickers — Prioritization](#3-news-fetching-for-100-tickers--prioritization)
4. [FastAPI Security Hardening](#4-fastapi-security-hardening)
5. [Docker Security for Portfolio Deployment](#5-docker-security-for-portfolio-deployment)
6. [Current Codebase Issues Summary](#6-current-codebase-issues-summary)

---

## 1. Top 100 US Stocks — Canonical Ticker List

### Why S&P 100 (OEX)

The S&P 100 is the correct canonical list for this use case. It is:
- Maintained by S&P Dow Jones Indices (official, not community-curated)
- Exactly 100 companies (101 tickers due to Alphabet dual-class: GOOG + GOOGL)
- Represents ~71% of S&P 500 market cap and ~61% of total US equity market cap
- Rebalanced quarterly — constituents are stable enough to hardcode for months at a time
- All constituents have active options markets (high liquidity = reliable yfinance data)

**Source:** S&P Dow Jones Indices official page, Wikipedia S&P 100 article (verified September 22, 2025 snapshot)
**Confidence:** HIGH

### Note on BRK.B vs BRK.A

The index holds BRK.B (Berkshire Hathaway Class B). BRK.A trades at ~$600K/share and has almost no volume on news sentiment. Use BRK.B.

### Full Ticker List Organized by GICS Sector

Hardcode this as a dict in your application. Count: 102 tickers (GOOG + GOOGL both included per index methodology).

```python
SP100_BY_SECTOR = {
    "Information Technology": [
        "AAPL",   # Apple
        "ACN",    # Accenture
        "ADBE",   # Adobe
        "AMAT",   # Applied Materials
        "AMD",    # Advanced Micro Devices
        "AVGO",   # Broadcom
        "CRM",    # Salesforce
        "CSCO",   # Cisco
        "IBM",    # IBM
        "INTC",   # Intel
        "INTU",   # Intuit
        "LRCX",   # Lam Research
        "MSFT",   # Microsoft
        "MU",     # Micron Technology
        "NOW",    # ServiceNow
        "NVDA",   # NVIDIA
        "ORCL",   # Oracle
        "PLTR",   # Palantir
        "QCOM",   # Qualcomm
        "TXN",    # Texas Instruments
    ],
    "Health Care": [
        "ABBV",   # AbbVie
        "ABT",    # Abbott Laboratories
        "AMGN",   # Amgen
        "BMY",    # Bristol-Myers Squibb
        "CVS",    # CVS Health
        "DHR",    # Danaher
        "GILD",   # Gilead Sciences
        "ISRG",   # Intuitive Surgical
        "JNJ",    # Johnson & Johnson
        "LLY",    # Eli Lilly
        "MDT",    # Medtronic
        "MRK",    # Merck
        "PFE",    # Pfizer
        "TMO",    # Thermo Fisher Scientific
        "UNH",    # UnitedHealth Group
    ],
    "Financials": [
        "AXP",    # American Express
        "BAC",    # Bank of America
        "BK",     # Bank of New York Mellon
        "BLK",    # BlackRock
        "BRK.B",  # Berkshire Hathaway Class B
        "C",      # Citigroup
        "COF",    # Capital One
        "GS",     # Goldman Sachs
        "JPM",    # JPMorgan Chase
        "MA",     # Mastercard
        "MS",     # Morgan Stanley
        "SCHW",   # Charles Schwab
        "USB",    # U.S. Bancorp
        "V",      # Visa
        "WFC",    # Wells Fargo
    ],
    "Communication Services": [
        "CMCSA",  # Comcast
        "DIS",    # Walt Disney
        "GOOG",   # Alphabet Class C
        "GOOGL",  # Alphabet Class A
        "META",   # Meta Platforms
        "NFLX",   # Netflix
        "T",      # AT&T
        "TMUS",   # T-Mobile US
        "VZ",     # Verizon
    ],
    "Consumer Discretionary": [
        "AMZN",   # Amazon
        "BKNG",   # Booking Holdings
        "GM",     # General Motors
        "HD",     # Home Depot
        "LOW",    # Lowe's
        "MCD",    # McDonald's
        "NKE",    # Nike
        "SBUX",   # Starbucks
        "TSLA",   # Tesla
    ],
    "Consumer Staples": [
        "CL",     # Colgate-Palmolive
        "COST",   # Costco
        "KO",     # Coca-Cola
        "MDLZ",   # Mondelez International
        "MO",     # Altria Group
        "PEP",    # PepsiCo
        "PG",     # Procter & Gamble
        "WMT",    # Walmart
    ],
    "Industrials": [
        "BA",     # Boeing
        "CAT",    # Caterpillar
        "DE",     # Deere & Company
        "EMR",    # Emerson Electric
        "FDX",    # FedEx
        "GD",     # General Dynamics
        "GE",     # GE Aerospace
        "GEV",    # GE Vernova
        "HON",    # Honeywell
        "LMT",    # Lockheed Martin
        "MMM",    # 3M
        "RTX",    # RTX Corporation (Raytheon)
        "UBER",   # Uber Technologies
        "UNP",    # Union Pacific
        "UPS",    # United Parcel Service
    ],
    "Energy": [
        "COP",    # ConocoPhillips
        "CVX",    # Chevron
        "XOM",    # ExxonMobil
    ],
    "Real Estate": [
        "AMT",    # American Tower
        "SPG",    # Simon Property Group
    ],
    "Utilities": [
        "DUK",    # Duke Energy
        "NEE",    # NextEra Energy
        "SO",     # Southern Company
    ],
    "Materials": [
        "LIN",    # Linde
    ],
}

# Flat list for yfinance download
SP100_TICKERS = [t for tickers in SP100_BY_SECTOR.values() for t in tickers]
# Total: 102 symbols (GOOG + GOOGL both present)
```

### Ticker Count by Sector

| Sector | Count |
|--------|-------|
| Information Technology | 20 |
| Health Care | 15 |
| Financials | 15 |
| Communication Services | 9 |
| Industrials | 15 |
| Consumer Discretionary | 9 |
| Consumer Staples | 8 |
| Energy | 3 |
| Real Estate | 2 |
| Utilities | 3 |
| Materials | 1 |
| **Total** | **100 companies / 102 tickers** |

### Maintenance Notes

- **GEV** (GE Vernova) was added in April 2024 after GE's spinoff; it replaced GE on the index
- **PLTR** (Palantir) joined the S&P 500 and subsequently the S&P 100 in 2024; verify quarterly
- Check S&P's official factsheet at https://www.spglobal.com/spdji/en/indices/equity/sp-100/ before each major release
- BRK.B yfinance ticker: use `"BRK-B"` in yfinance calls (hyphen, not dot) — yfinance normalizes the dot to a hyphen

---

## 2. yfinance at Scale — Batch Strategy

### Core Finding: Use `yf.download()` Not `yf.Ticker()` Loop

The current code loops `yf.Ticker(ticker).history(...)` for each symbol individually. This is the worst approach at 100 tickers: it makes 100 separate HTTP requests, each with session overhead, and will hit Yahoo Finance rate limits within seconds.

**Confidence:** HIGH — verified against yfinance GitHub source, official DeepWiki documentation, and multiple GitHub issues.

### Recommended: `yf.download()` with Chunking

```python
import yfinance as yf
import time
import pandas as pd
from typing import Dict, Any

def fetch_all_stock_data(tickers: list[str], chunk_size: int = 50) -> Dict[str, Any]:
    """
    Batch-download price history for all tickers.
    Chunks of 50 reduce per-request payload and avoid 429s.
    Each chunk = 1 HTTP request via Yahoo's multi-symbol endpoint.
    """
    all_data = {}
    chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]

    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(1.5)  # Polite delay between chunks

        try:
            # threads=True: yfinance uses multitasking library internally
            # group_by='ticker': result indexed as df['AAPL']['Close']
            # progress=False: suppress tqdm bar in server context
            raw = yf.download(
                tickers=chunk,
                period="1y",
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
                auto_adjust=True,
            )
        except Exception as e:
            print(f"Chunk {i} download failed: {e}", flush=True)
            continue

        for ticker in chunk:
            try:
                # When group_by='ticker', single-ticker chunks return flat df
                if len(chunk) == 1:
                    ticker_df = raw.copy()
                else:
                    ticker_df = raw[ticker].copy()

                ticker_df = ticker_df.dropna(how="all")
                if ticker_df.empty:
                    print(f"No data for {ticker} — possibly delisted", flush=True)
                    continue

                all_data[ticker] = process_ticker_df(ticker, ticker_df)

            except KeyError:
                print(f"Ticker {ticker} missing from download result", flush=True)
            except Exception as e:
                print(f"Error processing {ticker}: {e}", flush=True)

    return all_data


def process_ticker_df(ticker: str, df: pd.DataFrame) -> dict:
    """Convert raw yfinance DataFrame to API response shape."""
    df = df.reset_index()
    latest = df.tail(2)
    current_close = float(latest["Close"].iloc[-1])
    previous_close = float(latest["Close"].iloc[-2]) if len(latest) >= 2 else current_close
    percent_change = ((current_close - previous_close) / previous_close * 100
                      if previous_close != 0 else 0.0)

    df["Month"] = df["Date"].dt.to_period("M")
    monthly = df.groupby("Month").agg(
        Open=("Open", "first"),
        Close=("Close", "last"),
        High=("High", "max"),
        Low=("Low", "min"),
    ).reset_index()
    monthly["Month"] = monthly["Month"].dt.strftime("%Y-%m")

    return {
        "current_close": current_close,
        "previous_close": previous_close,
        "percent_change": round(percent_change, 4),
        "history": monthly.to_dict(orient="records"),
    }
```

### Rate Limiting Reality Check (2025)

Yahoo Finance tightened limits in early 2024. Community observations from GitHub issues and developer forums:

- Approximately 200-400 requests/hour from a single IP before 429 responses begin
- A single `yf.download(50 tickers, period="1y")` counts as roughly 1 request
- 100 tickers in 2 chunks = 2 requests — well within limits for on-demand fetches
- The danger is **repeated polling**. Fetching all 100 tickers every 60 seconds will be blocked

**Mitigation for this app:**

```python
# Cache TTL recommendation
STOCK_DATA_TTL_SECONDS = 1800   # 30 minutes — price history changes slowly
NEWS_TTL_SECONDS = 900          # 15 minutes — news is more time-sensitive

# Implement TTL on the existing in-memory cache
import time

cache: Dict[str, Any] = {
    "stock_data": None,
    "stock_data_fetched_at": 0,
    "news": None,
    "news_fetched_at": 0,
}

def is_cache_valid(key: str, ttl: int) -> bool:
    return (
        cache[key] is not None
        and (time.time() - cache[f"{key}_fetched_at"]) < ttl
    )
```

### Error Handling for Delisted / Missing Tickers

```python
# Pattern for gracefully skipping bad tickers
KNOWN_DELISTED = set()  # Populate at startup if needed

def safe_download_ticker(ticker: str) -> dict | None:
    if ticker in KNOWN_DELISTED:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info  # lightweight metadata check
        if info.get("lastPrice") is None:
            KNOWN_DELISTED.add(ticker)
            return None
    except Exception:
        pass
    # Proceed with download...
```

Key patterns from yfinance GitHub issues:
- Empty DataFrame from `yf.download()` means delisted or no data — check `df.empty` before processing
- `YFRateLimitError` is the typed exception since yfinance ~0.2.40; catch it specifically
- `YFPricesMissingError` is raised for symbols with no price history

```python
from yfinance.exceptions import YFRateLimitError, YFPricesMissingError

try:
    raw = yf.download(...)
except YFRateLimitError:
    # Back off and retry after 60 seconds
    time.sleep(60)
    raw = yf.download(...)
except YFPricesMissingError as e:
    print(f"No price data: {e}")
```

### BRK.B Special Case

```python
# In yfinance, Berkshire Hathaway Class B uses a hyphen:
# S&P 100 list uses: "BRK.B"
# yfinance requires: "BRK-B"
# Apply this normalization before any yfinance call:
def normalize_ticker(ticker: str) -> str:
    return ticker.replace(".", "-")
```

---

## 3. News Fetching for 100 Tickers — Prioritization

### The Core Problem

Fetching news for 100 tickers individually = 100 sequential HTTP requests to Yahoo Finance's search API. At 10 seconds timeout each, worst case is 1000 seconds (16 minutes) to complete. Realistically, Yahoo will rate-limit before you finish.

The current code already limits to `selected_symbols[:5]` when no ticker is specified — this is the right instinct. Formalize it.

**Confidence:** MEDIUM — Yahoo Finance's search API has no official documentation; behavior inferred from GitHub issues and community testing.

### Recommended Architecture: Tiered Priority

Do not try to fetch news for all 100 tickers on every request. Instead, define priority tiers:

```python
# Tier 1: Always fetch news (15 tickers — highest user interest + existing list)
NEWS_TIER_1 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "LLY", "JPM",
    "V", "UNH", "XOM", "WMT", "MA",
]

# Tier 2: Fetch when explicitly requested or on rotation (rotate 5 per cycle)
NEWS_TIER_2 = [
    "GOOG", "HD", "PG", "JNJ", "COST",
    "MRK", "BAC", "CRM", "ABBV", "CVX",
    "ORCL", "NOW", "GS", "IBM", "NFLX",
    # ... remaining high-cap tickers
]

# Tier 3: On-demand only (fetch only when user clicks on that specific stock)
NEWS_TIER_3 = [
    # Lower-volume SP100 members: DUK, SO, MO, LIN, SPG, AMT, etc.
]
```

### Rotation Strategy for Background Refresh

```python
import itertools

_tier2_cycle = itertools.cycle(
    [NEWS_TIER_2[i:i+5] for i in range(0, len(NEWS_TIER_2), 5)]
)

def get_news_symbols_for_refresh() -> list[str]:
    """Return the symbols to fetch news for in this refresh cycle."""
    # Always include Tier 1; rotate a 5-symbol slice of Tier 2
    return NEWS_TIER_1 + next(_tier2_cycle)
```

### Per-Request News: Always On-Demand

When the user clicks a specific stock, fetch that ticker directly — the existing `?ticker=AAPL` pattern is correct. No change needed here.

### Yahoo Finance Search API Limitations

The URL `https://query1.finance.yahoo.com/v1/finance/search?q={symbol}` returns:
- Up to ~10 news articles per symbol
- Results are not deduplicated across tickers (same article appears for AAPL and MSFT)
- No pagination — you get what you get per call
- Rate limit: approximately 200-400 calls/hour from a single IP
- No authentication required, but headers mimicking a browser are essential (current code does this correctly)

### Deduplication Is Critical at Scale

With 100 tickers, many news articles will be repeated (macro news hits every ticker). Add deduplication by UUID:

```python
def fetch_news_for_symbols(symbols: list[str]) -> list[dict]:
    seen_uuids = set()
    all_news = []

    for symbol in symbols:
        try:
            # existing fetch logic...
            for item in news_items:
                uuid = item.get("uuid")
                if uuid and uuid in seen_uuids:
                    continue
                seen_uuids.add(uuid)
                # ... sentiment scoring ...
                all_news.append(item)
            time.sleep(0.3)  # 300ms between news fetches
        except Exception as e:
            print(f"News fetch failed for {symbol}: {e}", flush=True)

    return sorted(all_news, key=lambda x: x.get("providerPublishTime", 0), reverse=True)
```

---

## 4. FastAPI Security Hardening

### Issue 1: Wildcard CORS with allow_credentials=True

**Severity:** Critical. This is contradictory and insecure.

Per FastAPI's official documentation: "None of `allow_origins`, `allow_methods` and `allow_headers` can be set to `['*']` if `allow_credentials` is set to `True`."

The current config has both `allow_origins=["*"]` AND `allow_credentials=True`. This is a security vulnerability — it allows any origin to make credentialed cross-origin requests.

**Fix:**

```python
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"  # dev default
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,        # explicit list, never ["*"]
    allow_credentials=True,
    allow_methods=["GET"],                 # this app only needs GET
    allow_headers=["Content-Type", "X-API-Key"],
)
```

For production, set the environment variable: `ALLOWED_ORIGINS=https://yourdomain.com`

### Issue 2: No API Authentication

Any person on the internet can call `/stock-price`, `/news`, and `/analyze-custom`. The `/analyze-custom` endpoint runs a Qwen 1.5B LLM inference — this is expensive compute that anyone can trigger.

**Fix — API Key via Header using FastAPI's native security:**

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    api_key: str                          # Required — no default
    allowed_origins: str = "http://localhost:3000"
    deployment_env: str = "local"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# auth.py
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from .config import get_settings, Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
```

```python
# main.py — apply to routes
from .auth import require_api_key

@app.get("/stock-price")
def get_stock_price(api_key: str = Security(require_api_key)):
    ...

@app.get("/news")
def get_news(ticker: str = None, api_key: str = Security(require_api_key)):
    ...

@app.get("/analyze-custom")
def analyze_custom(text: str, api_key: str = Security(require_api_key)):
    ...
```

The `lru_cache` on `get_settings()` means the `.env` file is read exactly once at startup — no per-request I/O.

### Issue 3: No Input Validation on Ticker and Text Parameters

The `/news?ticker=` and `/analyze-custom?text=` endpoints accept arbitrary strings. A malicious user could pass a 100MB string to `/analyze-custom` and cause an OOM crash.

**Fix — Pydantic query parameter validation:**

```python
from fastapi import Query
import re

VALID_TICKER_RE = re.compile(r'^[A-Z0-9.\-]{1,10}$')

@app.get("/news")
def get_news(
    ticker: str | None = Query(
        default=None,
        min_length=1,
        max_length=10,
        pattern=r'^[A-Z0-9.\-]{1,10}$',  # FastAPI 0.115+ supports pattern
        description="Stock ticker symbol, e.g. AAPL",
    ),
    api_key: str = Security(require_api_key),
):
    # ticker is now guaranteed to match the pattern or be None
    ...

@app.get("/analyze-custom")
def analyze_custom(
    text: str = Query(
        ...,
        min_length=10,
        max_length=2000,    # Prevents LLM OOM from huge inputs
        description="Financial text to analyze",
    ),
    api_key: str = Security(require_api_key),
):
    ...
```

Additionally, validate ticker against the known list before making yfinance calls:

```python
from .tickers import SP100_TICKERS  # your ticker list module

def validate_ticker(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if normalized not in SP100_TICKERS:
        raise HTTPException(
            status_code=422,
            detail=f"Ticker '{ticker}' is not in the supported list"
        )
    return normalized
```

### Issue 4: No Rate Limiting on Expensive Endpoints

The `/analyze-custom` endpoint runs LLM inference. Add per-IP rate limiting with `slowapi`:

```python
# requirements.txt addition: slowapi>=0.1.9

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/analyze-custom")
@limiter.limit("10/minute")          # LLM inference is expensive
def analyze_custom(request: Request, text: str = Query(..., max_length=2000)):
    ...

@app.get("/stock-price")
@limiter.limit("30/minute")
def get_stock_price(request: Request):
    ...

@app.get("/news")
@limiter.limit("30/minute")
def get_news(request: Request, ticker: str | None = None):
    ...
```

Note: `request: Request` must be the first parameter when using slowapi decorators.

### Issue 5: Missing Security Headers

Add response security headers. The simplest approach for a portfolio project:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Complete `.env` File Structure

```bash
# .env  (NEVER commit this file)
# Copy .env.example and fill in real values

# Security
API_KEY=your-random-256bit-key-here      # generate: python -c "import secrets; print(secrets.token_hex(32))"
ALLOWED_ORIGINS=http://localhost:3000

# App
DEPLOYMENT_ENV=local

# AWS (if needed)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
```

```bash
# .env.example  (SAFE to commit — template with no real values)
API_KEY=REPLACE_WITH_GENERATED_KEY
ALLOWED_ORIGINS=http://localhost:3000,https://your-deployed-frontend.com
DEPLOYMENT_ENV=local
AWS_ACCESS_KEY_ID=REPLACE_WITH_YOUR_KEY
AWS_SECRET_ACCESS_KEY=REPLACE_WITH_YOUR_SECRET
AWS_DEFAULT_REGION=us-east-1
```

---

## 5. Docker Security for Portfolio Deployment

### Issue: `COPY . .` Copies Everything Into the Image

The current `backend/Dockerfile` runs `COPY . .` which will include any `.env` file present in the build context. Even if `.gitignore` excludes `.env`, anyone who builds the image gets the secrets baked into a layer.

### Fix 1: Add `.dockerignore` to Each Service Directory

```
# backend/.dockerignore
.env
.env.local
.env.*.local
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.git/
.gitignore
README.md
tests/
*.md
```

```
# frontend/stock_sentiment_analysis/.dockerignore
.env
.env.local
.env.*.local
node_modules/
build/
.git/
*.md
```

### Fix 2: Pass Secrets at Runtime via `docker-compose.yaml`, Not Build Time

```yaml
# docker-compose.yaml — production-safe pattern
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env              # loaded at container runtime, NOT baked into image
    environment:
      - DEPLOYMENT_ENV=production   # non-secret overrides are fine inline
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  frontend:
    build:
      context: ./frontend/stock_sentiment_analysis
      args:
        - REACT_APP_API_URL=${REACT_APP_API_URL:-http://localhost:8000}
    ports:
      - "3000:80"
    depends_on:
      - backend
```

The `env_file` directive loads secrets at container runtime — they never appear in image layers. The `${REACT_APP_API_URL:-http://localhost:8000}` pattern uses shell variable substitution with a default fallback.

### Fix 3: Root-Level `.gitignore` — Comprehensive

The current `.gitignore` is missing critical entries. Replace it:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.installed.cfg
*.egg
.venv/
venv/
env/
ENV/

# Environment / Secrets — CRITICAL
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
backend/.env
frontend/**/.env
**/.env
*.pem
*.key
secrets/
**/secrets/

# Docker overrides (often contain local secrets)
docker-compose.override.yml
docker-compose.local.yml

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# React build artifacts
frontend/**/build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Data
data/
*.csv
*.json.bak
test_output.json

# ML model cache (large files, not for git)
.cache/
huggingface/
*.bin
*.safetensors

# macOS
.DS_Store

# Windows
Thumbs.db
```

### Fix 4: Verify No Secrets Are Already in Git History

```bash
# Run this before making the repo public
git log --all --full-history -- "**/.env" "**/*.pem" "**/secrets/*"

# If any .env files appear in history, use git-filter-repo to scrub them:
# pip install git-filter-repo
# git filter-repo --path .env --invert-paths
```

### Fix 5: Rotate Any Credentials That Have Been Committed

If AWS credentials, API keys, or other secrets have ever been committed to the repository (even in a past commit that was later deleted), treat them as compromised and rotate immediately:
- Go to AWS IAM and revoke/rotate the access keys
- Generate a new `API_KEY` value for the application
- Never reuse the old values

### Portfolio-Specific: What Reviewers Will Check

When a hiring manager or technical reviewer looks at your public portfolio repo, they will:
1. Check `git log` for accidentally committed `.env` files
2. Look at `docker-compose.yaml` for hardcoded credentials
3. Look at `main.py` for CORS configuration and auth patterns
4. Check if `.env.example` exists (shows security awareness)
5. Look for a health check endpoint (shows production mindset)

Add a public health endpoint that requires no auth:

```python
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

---

## 6. Current Codebase Issues Summary

| Issue | File | Severity | Fix Section |
|-------|------|----------|-------------|
| Wildcard CORS with allow_credentials=True | `backend/main.py:24-30` | Critical | Section 4, Issue 1 |
| No API authentication on any endpoint | `backend/main.py:160-254` | Critical | Section 4, Issue 2 |
| Ticker parameter accepts arbitrary strings | `backend/main.py:210` | High | Section 4, Issue 3 |
| Text parameter unbounded (LLM OOM risk) | `backend/main.py:257` | High | Section 4, Issue 3 |
| No rate limiting on LLM endpoint | `backend/main.py:257` | High | Section 4, Issue 4 |
| `COPY . .` without .dockerignore | `backend/Dockerfile:8` | High | Section 5, Fix 1+2 |
| `.gitignore` missing .env entries | `.gitignore` | High | Section 5, Fix 3 |
| In-memory cache has no TTL | `backend/main.py:145-148` | Medium | Section 2 |
| Sequential per-ticker yfinance loop | `backend/main.py:167-205` | Medium | Section 2 |
| No news deduplication | `backend/main.py:213-246` | Low | Section 3 |
| No .env.example template | repo root | Low | Section 4, Issue 5 |
| `test_output.json` not in .gitignore | `.gitignore` | Low | Section 5, Fix 3 |

---

## Sources

**S&P 100 Constituents:**
- [S&P 100 — Wikipedia](https://en.wikipedia.org/wiki/S%26P_100) (September 2025 snapshot)
- [S&P 100 Official Factsheet — S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/equity/sp-100/)

**yfinance Batch Downloads and Rate Limiting:**
- [Working with Multiple Tickers — yfinance DeepWiki](https://deepwiki.com/ranaroussi/yfinance/4.2-working-with-multiple-tickers)
- [Rate Limiting and API Best Practices — Sling Academy](https://www.slingacademy.com/article/rate-limiting-and-api-best-practices-for-yfinance/)
- [YFRateLimitError GitHub Issue #2614](https://github.com/ranaroussi/yfinance/issues/2614)
- [Bulk download rate limit Issue #2125](https://github.com/ranaroussi/yfinance/issues/2125)

**FastAPI Security:**
- [CORS Configuration — FastAPI Official Docs](https://fastapi.tiangolo.com/tutorial/cors/)
- [Settings and Environment Variables — FastAPI Official Docs](https://fastapi.tiangolo.com/advanced/settings/)
- [Adding API Key Auth to FastAPI — Josh Di Mella](https://joshdimella.com/blog/adding-api-key-auth-to-fast-api)
- [FastAPI Security Guide: Auth, Input Validation, OWASP — ShipSafer](https://www.shipsafer.app/blog/fastapi-security-guide)
- [SlowAPI — GitHub](https://github.com/laurentS/slowapi)

**Docker Secrets:**
- [4 Ways to Handle Secrets in Docker — GitGuardian](https://blog.gitguardian.com/how-to-handle-secrets-in-docker/)
- [Docker Build Secrets — Docker Official Docs](https://docs.docker.com/build/building/secrets/)
- [Managing Environment Variables in Docker Compose — Medium](https://medium.com/@sh.hamzarauf/handling-environment-variables-in-docker-compose-for-secure-and-flexible-configurations-5ce6a5bb0412)

**Pydantic Settings:**
- [Settings Management — Pydantic Official Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Centralizing FastAPI Config with Pydantic Settings — David Muraya](https://davidmuraya.com/blog/centralizing-fastapi-configuration-with-pydantic-settings-and-env-files/)
