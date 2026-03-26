# External Integrations

**Analysis Date:** 2026-03-26

## APIs & External Services

**Yahoo Finance (Stock Data):**
- Purpose: Fetches 1-year daily price history, calculates monthly OHLC aggregations, and retrieves ticker-linked news articles
- SDK/Client: `yfinance` Python package (`Ticker.history()`, `Ticker.get_news()`) in `backend/main.py` and `backend/fetch_latest_news.py`
- Direct HTTP: `requests.get("https://query1.finance.yahoo.com/v1/finance/search?q={symbol}")` in `backend/main.py` for the `/news` endpoint (filters out premium articles)
- Auth: No API key required; uses public endpoints with a spoofed browser `User-Agent` header
- Rate limiting: 10-second socket timeout set globally via `socket.setdefaulttimeout(10)`

**Hugging Face Model Hub (ML Models):**
- Purpose: Downloads pre-trained NLP models at container startup
- Models pulled at runtime:
  - `ProsusAI/finbert` — FinBERT financial sentiment classifier, loaded via `transformers.pipeline("sentiment-analysis", ...)`
  - `Qwen/Qwen2.5-1.5B-Instruct` — lightweight instruction-tuned LLM for reasoning, loaded via `AutoModelForCausalLM.from_pretrained(...)`
- Auth: No API key required for public models; Hugging Face cache stored in default `~/.cache/huggingface/` inside the container
- Files: `backend/main.py` lines 41-57

**AWS API Gateway (Backend Production Hosting):**
- Purpose: Exposes the FastAPI backend publicly in the production environment
- Endpoints (hardcoded fallbacks in frontend):
  - `https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/stock-price` — production endpoint, used in `src/apis/api.js`
  - `https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/news` — production endpoint, used in `src/apis/api.js`
  - `https://ip8z0jodq4.execute-api.us-east-1.amazonaws.com/test/stock-price` — older test-stage endpoint, used in `src/utils/getStockData.js`
- Auth: No request signing or API key observed in client code; endpoints appear publicly accessible
- Region: `us-east-1`

**AWS S3 (News Data Storage — Legacy Script):**
- Purpose: Stores fetched news articles as JSON objects for pipeline use
- Bucket: `fetch-latest-news`
- Key written: `latest_articles.json`
- Client: `boto3.client('s3')` in `backend/fetch_latest_news.py`
- Auth: Hardcoded `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` directly in `backend/fetch_latest_news.py` lines 8-9 — **these are plaintext secrets committed to source; they must be rotated and moved to environment variables**

**AWS DynamoDB (Stock History Storage — Legacy Script):**
- Purpose: Creates per-ticker tables (e.g., `AAPL_Historical_Data`) and batch-writes monthly OHLC records
- Client: `boto3.resource('dynamodb')` and `boto3.client('dynamodb')` in `backend/create_add_monthly_stock_data.py`
- Auth: Uses ambient AWS credentials (no keys hardcoded in this file); relies on environment-level credential chain (IAM role, env vars, or `~/.aws/credentials`)
- Note: The `create_table_and_push()` call is commented out in `__main__`; current script writes to a local JSON file instead

**AWS Comprehend (Sentiment Analysis — Legacy Script):**
- Purpose: Chunk-based sentiment detection on article text; aggregates `Positive`, `Negative`, `Neutral`, `Mixed` scores per article
- Client: `boto3.client('comprehend')` in `backend/SentimentAnalysis.py`
- Method: `comprehend.detect_sentiment(Text=chunk, LanguageCode='en')` with max 4000 chars per chunk
- Auth: Uses ambient AWS credentials (no keys hardcoded in this file)
- Status: Standalone script (`__main__` block); not integrated into the FastAPI server

**AWS Amplify (Frontend Hosting — Partially Configured):**
- Purpose: CI/CD pipeline and hosting for the React frontend
- Config files: `frontend/stock_sentiment_analysis/amplify.yml`, `amplify/.config/project-config.json`, `amplify/backend/backend-config.json`
- Build: `npm ci` → `npm run build`; artifact dir `build/`
- Backend resources: Empty (`backend-config.json` is `{}`); no Amplify Auth, API, or Storage categories are provisioned despite the SDK being installed (`aws-amplify` ^6.0.21, `@aws-amplify/ui-react` ^6.1.6)
- Provider: `awscloudformation`

## Data Storage

**Databases:**
- AWS DynamoDB — per-ticker historical stock tables (`{TICKER}_Historical_Data`); used only in `backend/create_add_monthly_stock_data.py` (currently effectively disabled)
- No SQL/relational database present

**File Storage:**
- AWS S3 bucket `fetch-latest-news` — JSON news payload storage via `backend/fetch_latest_news.py`
- Local filesystem — `data/nasdaq_exteral_data.csv` referenced in `config.py` (offline preprocessing input); `data/stock_data.json` and `data/final_data.json` written by preprocessing scripts
- In-memory dict cache in `backend/main.py` — `cache = {"stock_data": None, "news": None}` — caches first successful fetch for the lifetime of the process; **no TTL, no persistence, no invalidation mechanism**

**Caching:**
- In-process Python dict in `backend/main.py`; resets on server restart; no external cache (no Redis, Memcached, etc.)

## Authentication & Identity

**Backend API:**
- No authentication on any FastAPI endpoint; all routes (`/stock-price`, `/news`, `/analyze-custom`) are publicly accessible
- CORS configured with `allow_origins=["*"]`

**Frontend:**
- `aws-amplify` and `@aws-amplify/ui-react` are installed but no Amplify Auth category is provisioned; no login/auth UI is present in the application

**AWS CLI/SDK:**
- Legacy scripts in `backend/` use hardcoded credentials (`fetch_latest_news.py`) or ambient credential chain (`SentimentAnalysis.py`, `create_add_monthly_stock_data.py`)

## Environment Variables

**Backend (loaded via `python-dotenv` from `.env`):**
- `DEPLOYMENT_ENV` — set to `local` in `docker-compose.yaml`; read at runtime (exact usage in `main.py` not shown beyond env loading)
- AWS credentials should be supplied as env vars but are currently hardcoded in `backend/fetch_latest_news.py`

**Frontend (React build-time via `REACT_APP_` prefix):**
- `REACT_APP_API_URL` — base URL for all backend API calls; set to `http://localhost:8000` in `docker-compose.yaml`; if absent, falls back to the hardcoded AWS API Gateway production URL
  - Used in: `src/apis/api.js`, `src/utils/getStockData.js`, `src/components/CustomSentiment/CustomSentiment.js`
- `.env` file present at `frontend/stock_sentiment_analysis/.env` (not read; contents not inspected)

**Docker Compose environment block:**
```
backend:
  DEPLOYMENT_ENV=local

frontend:
  REACT_APP_API_URL=http://localhost:8000
```

## Webhooks & Event Streams

**Incoming:**
- None detected

**Outgoing:**
- None detected; the backend is purely request/response with no webhook dispatch

## Monitored / Tracked Symbols

The following 15 stock tickers are hardcoded in `config.py` and `backend/main.py` as the universe of tracked companies:

```
AAPL, AMZN, AMD, BA, BX, COST, CRM, DIS, GOOG, GS, IBM, INTC, MS, NKE, NVDA
```

These drive the `/stock-price` bulk fetch and the default `/news` batch (first 5 symbols only for performance).

---

*Integration audit: 2026-03-26*
