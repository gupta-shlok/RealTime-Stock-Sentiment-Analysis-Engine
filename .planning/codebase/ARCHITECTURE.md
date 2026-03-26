# Architecture

**Analysis Date:** 2026-03-26

## Pattern Overview

**Overall:** Two-tier client-server with AI inference pipeline

**Key Characteristics:**
- React SPA frontend communicates with a FastAPI backend over REST HTTP
- Backend performs all data retrieval, sentiment scoring, and in-memory caching — no separate database layer
- AI inference runs in-process on the backend using two models loaded at startup (FinBERT + Qwen2.5)
- The frontend holds global stock data in a React Context, fetched once at app load; news is fetched per-component or per-route on demand
- Originally deployed to AWS (API Gateway, Lambda, S3, DynamoDB, Comprehend); now replaced with Docker Compose for local execution and a FastAPI backend for cloud deployment

---

## System Layers

**Presentation Layer — React SPA:**
- Purpose: Renders the dashboard UI, routes between pages, displays stock and news data with sentiment badges
- Location: `frontend/stock_sentiment_analysis/src/`
- Contains: Page-level components, display-only leaf components, one context provider, one API client module
- Depends on: Backend REST API via `src/apis/api.js`
- Used by: End users via browser

**API Layer — FastAPI:**
- Purpose: Exposes three HTTP endpoints; orchestrates data retrieval from Yahoo Finance, runs sentiment models, and returns JSON
- Location: `backend/main.py`
- Contains: All route handlers, model initialization, in-memory cache dict, helper functions
- Depends on: `yfinance` (price data), Yahoo Finance search API (news), HuggingFace `transformers` (FinBERT, Qwen2.5)
- Used by: Frontend API client; also directly accessible via Swagger UI at `/docs`

**Inference Layer — Embedded ML Models:**
- Purpose: Scores financial text sentiment on a [-1, 1] scale; provides reasoning narrative for custom queries
- Location: Inside `backend/main.py` (loaded at process startup)
- Contains:
  - `finbert_pipe` — HuggingFace pipeline wrapping `ProsusAI/finbert`; fast financial domain classifier
  - `qwen_model` / `qwen_tokenizer` — `Qwen/Qwen2.5-1.5B-Instruct`; chat-format LLM for reasoning
- Depends on: `torch`, `transformers`, `accelerate`; uses CUDA if available, falls back to CPU
- Used by: `/news` endpoint (FinBERT only, for speed), `/analyze-custom` endpoint (60% FinBERT + 40% Qwen ensemble)

**Data / Cache Layer — In-Memory Dict:**
- Purpose: Prevents redundant Yahoo Finance fetches within a single server lifetime
- Location: `backend/main.py`, lines 145–148 (`cache` dict)
- Contains: `cache["stock_data"]` (all 15 tickers, fetched once), `cache["news"]` (latest 20 articles, fetched once when no ticker filter)
- Limitation: Cache is never invalidated; restarting the process is the only way to refresh data

---

## Data Flow

**Stock Price Flow (app load):**

1. React app mounts; `StockDataProvider` in `src/context/StockDataContext.js` calls `getStockData()` from `src/apis/api.js`
2. `api.js` sends `GET /stock-price` to the backend (URL from `REACT_APP_API_URL` env var, falling back to a hardcoded AWS API Gateway URL)
3. `backend/main.py` → `get_stock_price()` checks `cache["stock_data"]`; if empty, iterates over all 15 tickers in `selected_symbols`, calls `yf.Ticker(ticker).history(period='1y', interval='1d')` for each, aggregates monthly OHLC data, computes day-over-day percent change
4. Response JSON: `{ "AAPL": { current_close, previous_close, percent_change, history: [{Month, Open, Close, High, Low}] }, ... }`
5. Context transforms the dict into an array: `[{ name: "AAPL", current_close, ... }]` and stores it in `stockData` state
6. `StockChart` reads context → renders a horizontally scrolling ticker strip via `StockDetails` cards
7. `TopCompanies` reads context → sorts by `current_close` descending → renders `CompanyTicker` rows
8. `CompanyPage` reads context → finds the matching ticker object → renders the 1-year area chart and metrics grid

**News Feed Flow (homepage load):**

1. `NewsData` component mounts; calls `getNewsData()` with no ticker argument from `src/apis/api.js`
2. `api.js` sends `GET /news` (no query param) to the backend
3. `backend/main.py` → `get_news()` checks `cache["news"]`; if empty, iterates first 5 symbols in `selected_symbols`
4. For each symbol, hits `https://query1.finance.yahoo.com/v1/finance/search?q={symbol}`, filters out premium articles
5. Each non-premium article title is run through `analyze_sentiment_ensemble()` → `finbert_score()` → appends `sentiment_score` (float) and `sentiment_label` (string) to each article object
6. Articles sorted by `providerPublishTime` descending, truncated to 20, cached, returned as JSON array
7. `NewsData` renders: first article as large card (`NewsItem`), next 3 as small cards, then `TopCompanies` sidebar

**Company-Specific News Flow (route navigation):**

1. User selects a ticker via `SearchBar` (MUI Autocomplete) or clicks a `CompanyTicker` link → React Router navigates to `/company/:ticker`
2. `CompanyPage` mounts; calls `getNewsData(ticker)` with the ticker symbol as query param
3. `api.js` sends `GET /news?ticker=AAPL` (example) to the backend
4. `get_news()` fetches Yahoo Finance search results for that single ticker only; result is NOT cached
5. All returned articles rendered as `NewsItem` cards in the company news grid

**Custom Sentiment Flow (user-initiated):**

1. User navigates to `/custom-sentiment` → `CustomSentiment` component renders a textarea and submit button
2. On submit, `CustomSentiment` sends `GET /analyze-custom?text=<user_text>` directly via `axios` (no api.js abstraction)
3. `backend/main.py` → `analyze_custom()`:
   - Runs `finbert_score(text)` → signed float in [-1, 1]
   - Runs `get_qwen_analysis(text)` → applies chat template, generates up to 100 tokens, parses JSON response for `sentiment`, `confidence`, `reason`
   - Blends: `0.6 * finbert_score + 0.4 * qwen_score`
4. Response: `{ score, label, finbert_score, llm_score, reasoning, model }` rendered in a result card with Bullish/Bearish/Neutral label

---

## Key Components and Responsibilities

**`backend/main.py`**
Single-file backend. Owns model loading, all endpoint definitions, the in-memory cache, Yahoo Finance fetching, and sentiment scoring. There is no module separation — all logic lives in this one file.

**`src/context/StockDataContext.js`**
React Context provider wrapping the entire app. Fetches stock price data once on mount and exposes it as an array to all descendant components via `useContext(StockDataContext)`.

**`src/apis/api.js`**
Central HTTP client for the frontend. Exports two functions: `getStockData()` and `getNewsData(ticker?)`. Uses `axios`. Respects `REACT_APP_API_URL` env var with an AWS API Gateway URL as fallback.

**`src/components/CompanyPage/CompanyPage.js`**
Detail page for a single stock. Reads stock data from context (pre-loaded), fetches ticker-specific news on mount, renders a 1-year area chart (Recharts `AreaChart`), three metric cards, and a news grid.

**`src/components/NewsData/NewsData.js`**
Homepage news section. Fetches all news on mount, renders the first article large, the next three small, then passes control to `TopCompanies` for the sidebar.

**`src/components/NewsItem/NewsItem.js`**
Leaf display component. Renders a linked article card with image and a sentiment badge (`Bullish`/`Bearish`/`Neutral`) derived from the `sentiment_score` float on the news object.

**`src/components/CustomSentiment/CustomSentiment.js`**
Standalone page. Manages its own local state (`text`, `result`, `loading`). Makes a direct axios call to `/analyze-custom`, displays the ensemble result card with score, label, and Qwen reasoning.

**`src/components/StockChart/StockChart.js`**
Renders a horizontally scrolling strip of `StockDetails` cards by mapping over the context array.

**`src/components/TopBar/TopBar.js`**
Persistent navigation bar rendered outside `<Routes>`. Contains the app logo (links to `/`), a `SearchBar` autocomplete, and a nav link that toggles between `/custom-sentiment` and `/`.

**`src/components/SearchBar/SearchBar.js`**
MUI `Autocomplete` populated with the hardcoded 15-ticker list. On selection, uses `useNavigate` to push `/company/:ticker`.

---

## Communication Patterns

**Frontend → Backend: REST over HTTP**
- All communication is synchronous HTTP GET requests via `axios`
- No WebSockets, no polling, no streaming
- Three endpoints:
  - `GET /stock-price` — returns all 15 tickers' current price and 1-year monthly OHLC history
  - `GET /news[?ticker=SYMBOL]` — returns up to 20 news articles with sentiment scores
  - `GET /analyze-custom?text=<string>` — returns ensemble sentiment score and LLM reasoning
- CORS wildcard (`allow_origins=["*"]`) configured on FastAPI

**Backend → External APIs:**
- `yfinance` library calls Yahoo Finance for stock price history (HTTPS)
- Direct `requests.get` to `https://query1.finance.yahoo.com/v1/finance/search` for news
- HuggingFace model weights downloaded from HuggingFace Hub on first startup

**Dual URL strategy in `api.js`:**
- If `REACT_APP_API_URL` is set (Docker, local dev): requests go to that URL (e.g., `http://localhost:8000`)
- If unset (legacy / production): requests fall back to a hardcoded AWS API Gateway URL (`https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod`)

---

## State Management Approach

**Global state — React Context API:**
- `StockDataContext` (in `src/context/StockDataContext.js`) holds the array of all 15 stocks
- Populated once on app mount via a `useEffect` in `StockDataProvider`
- Consumed directly by `StockChart`, `TopCompanies`, and `CompanyPage` using `useContext`
- No state management library (no Redux, no Zustand)

**Local component state — `useState`:**
- `NewsData`: `newsItems`, `loading`
- `CompanyPage`: `companyNews`, `loadingNews`
- `CustomSentiment`: `text`, `result`, `loading`
- `SearchBar`: `searchTerm`

**Backend state — in-memory dict:**
- `cache["stock_data"]`: set on first `/stock-price` call, never evicted
- `cache["news"]`: set on first unfiltered `/news` call, never evicted
- Ticker-filtered news (`/news?ticker=X`) is never cached

---

*Architecture analysis: 2026-03-26*
