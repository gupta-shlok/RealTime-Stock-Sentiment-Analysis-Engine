# Codebase Concerns

**Analysis Date:** 2026-03-26

---

## Security Concerns

**CRITICAL: AWS credentials hardcoded in source code:**
- Issue: Real AWS Access Key ID and Secret Access Key are written in plaintext directly in the source file.
- Files: `backend/fetch_latest_news.py` lines 8–9
  ```
  AWS_ACCESS_KEY_ID = 'AKIA3FLD2AYWN7TZUV5X'
  AWS_SECRET_ACCESS_KEY = '6DFZfHeAflPSG5...'
  ```
- Impact: These credentials are committed to git history and any public exposure of this repo constitutes a full credential leak for the `fetch-latest-news` S3 bucket. Rotating these keys is the immediate required action.
- Fix approach: Remove credentials from source immediately, rotate them in AWS IAM, and load them via environment variables using `python-dotenv`. Never commit `.env` files.

**AWS account ID and IAM ARNs exposed in committed Amplify config:**
- Issue: `team-provider-info.json` is committed and contains the AWS account ID (`381492011036`), IAM role ARNs, CloudFormation stack IDs, and the Amplify App ID.
- Files: `frontend/stock_sentiment_analysis/amplify/team-provider-info.json`
- Impact: Exposes AWS account ID and resource identifiers, aiding reconnaissance for targeted attacks. This file is typically gitignored in Amplify projects.
- Fix approach: Add `amplify/team-provider-info.json` to `.gitignore`, rotate any credentials associated with the exposed account, and remove the file from git history with `git filter-repo`.

**Wildcard CORS policy on public API:**
- Issue: The FastAPI backend allows requests from any origin with `allow_origins=["*"]`.
- Files: `backend/main.py` lines 24–30
- Impact: Any website can make credentialed requests to the API. Combined with no authentication, the API is fully open to abuse.
- Fix approach: Restrict `allow_origins` to the specific frontend domain(s) (e.g., the Amplify-hosted URL and `localhost:3000`).

**No authentication or authorization on any API endpoint:**
- Issue: All three endpoints (`/stock-price`, `/news`, `/analyze-custom`) are publicly accessible with no API key, JWT, or session validation.
- Files: `backend/main.py`
- Impact: The `/analyze-custom` endpoint in particular is directly exploitable — it loads a 1.5B-parameter LLM on every call. Any attacker can trigger unlimited model inference, causing CPU/GPU exhaustion and cloud cost spikes.
- Fix approach: At minimum, require a shared API key via an `Authorization` header. Rate limiting per IP is also needed (see Performance section).

**Arbitrary text passed to LLM without length or content validation:**
- Issue: The `/analyze-custom` endpoint accepts a `text` query parameter with no length cap, content filtering, or sanitization before passing to Qwen2.5.
- Files: `backend/main.py` line 258: `def analyze_custom(text: str)`
- Impact: Enables prompt injection attacks against the Qwen model, and allows sending extremely long inputs to inflate inference time. The Qwen call itself only slices `text[:400]`, but the full string still traverses FastAPI and hits FinBERT at `text[:512]`.
- Fix approach: Add FastAPI `Query(max_length=2000)` validation. Consider a content moderation layer before LLM inference.

**Hardcoded public AWS API Gateway URL used as fallback:**
- Issue: Two separate files embed production AWS API Gateway URLs as fallback defaults when `REACT_APP_API_URL` is not set.
- Files:
  - `frontend/stock_sentiment_analysis/src/apis/api.js` lines 5, 19 (`pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod`)
  - `frontend/stock_sentiment_analysis/src/utils/getStockData.js` line 4 (`ip8z0jodq4.execute-api.us-east-1.amazonaws.com/test`)
- Impact: Development builds silently hit production infrastructure. Accidental production traffic during local development or tests. Two different gateway URLs suggest one may be stale/abandoned.
- Fix approach: Remove hardcoded URLs. Require `REACT_APP_API_URL` to be set; throw an explicit error if absent.

---

## Performance Concerns

**ML models loaded at module import time (blocking server startup):**
- Issue: FinBERT pipeline and Qwen2.5-1.5B are downloaded and loaded synchronously at module level (lines 41–57 of `main.py`), not inside an async lifespan event.
- Files: `backend/main.py` lines 36–58
- Impact: The server blocks all requests until both models finish loading (potentially several minutes on first run without a cache). Any Uvicorn worker restart cold-starts the full download. Docker containers do not cache the model weights between builds.
- Fix approach: Use FastAPI's `lifespan` context manager for model loading. Add a Docker volume or bind-mount for `~/.cache/huggingface` to avoid re-downloading on every container start.

**In-memory cache has no TTL and never expires:**
- Issue: `cache["stock_data"]` and `cache["news"]` are populated once and held for the entire process lifetime with no expiry, invalidation, or refresh mechanism.
- Files: `backend/main.py` lines 144–148, 162–163, 211–212
- Impact: Stock prices and news become stale immediately after first fetch. A server that stays alive for days will serve data that is weeks old. Restarting the server is the only way to refresh data.
- Fix approach: Add a timestamp to each cache entry and invalidate after a configurable TTL (e.g., 5 minutes for news, 15 minutes for stock prices). Use `asyncio` background tasks for proactive refresh.

**Synchronous yfinance calls block the async FastAPI event loop:**
- Issue: `yf.Ticker(ticker).history(...)` is a synchronous blocking HTTP call made directly inside async-compatible FastAPI route handlers. With 15 tickers looped serially, this blocks the entire Uvicorn worker.
- Files: `backend/main.py` lines 168–205
- Impact: During the initial cache miss, the `/stock-price` endpoint blocks for 15+ sequential network round-trips. No other request can be served during this time.
- Fix approach: Wrap yfinance calls in `asyncio.run_in_executor` or use `httpx` with async yfinance alternatives. Alternatively, pre-populate the cache at startup via a background task.

**Qwen2.5 inference runs synchronously on the request thread:**
- Issue: `get_qwen_analysis` runs LLM inference synchronously in the request handler with no timeout, no background task, and no queue.
- Files: `backend/main.py` lines 61–112, 265
- Impact: On CPU, a single `/analyze-custom` request can take 30–120 seconds, blocking all other requests on that Uvicorn worker. With default single-worker startup, this effectively stalls the entire server.
- Fix approach: Move LLM inference to a background worker queue (e.g., Celery, ARQ, or a simple `asyncio.Queue`). Return a job ID immediately and poll for results, or use WebSockets for streaming.

**News fetch only queries first 5 symbols for the homepage:**
- Issue: `search_symbols = [ticker] if ticker else selected_symbols[:5]` hard-limits the homepage news scan to 5 of 15 supported tickers.
- Files: `backend/main.py` line 222
- Impact: 10 out of 15 listed companies never appear in the homepage news feed. Users see an incomplete picture without any indication that coverage is partial.
- Fix approach: Either scan all 15 tickers with appropriate rate limiting, or document and surface the limitation in the UI.

**`Math.max(...spread)` on potentially large chartData arrays:**
- Issue: `CompanyPage` spreads the full `chartData` array into `Math.max` and `Math.min` for Year High/Low calculations.
- Files: `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js` lines 91, 95
- Impact: `Math.max(...array)` will throw `RangeError: Maximum call stack size exceeded` if `chartData` ever contains thousands of entries. For 1-year monthly aggregation this is safe today, but fragile if the data resolution changes to daily.
- Fix approach: Use `chartData.reduce` instead of spread: `chartData.reduce((max, d) => Math.max(max, d.High), -Infinity)`.

**Context mutation: `sort()` called directly on shared context array:**
- Issue: `TopCompanies` calls `stockData.sort(...)` directly on the array from context without copying it first.
- Files: `frontend/stock_sentiment_analysis/src/components/TopCompanies/TopCompanies.js` line 9
- Impact: `Array.prototype.sort` mutates in place. Every render of `TopCompanies` reorders the shared context array, which can cause other consumers of `StockDataContext` (like `StockChart`) to silently receive data in a different order than intended. This can also trigger unexpected re-renders.
- Fix approach: Use `[...stockData].sort(...)` to sort a copy.

---

## Tech Debt

**Duplicate `getStockData` utility with diverging API endpoints:**
- Issue: The same function — fetching stock price data — is implemented twice with different hardcoded fallback URLs:
  - `frontend/stock_sentiment_analysis/src/utils/getStockData.js` (unused utility, points to `/test` gateway)
  - `frontend/stock_sentiment_analysis/src/apis/api.js` (active, points to `/prod` gateway)
- Impact: The `utils/getStockData.js` file is never imported by any component; `StockDataContext` imports only from `apis/api.js`. Dead code that creates confusion about which URL is authoritative.
- Fix approach: Delete `src/utils/getStockData.js`. Consolidate all API calls in `src/apis/api.js`.

**Ticker symbol list duplicated across five separate locations:**
- Issue: The list `['AAPL', 'AMZN', 'AMD', 'BA', 'BX', 'COST', 'CRM', 'DIS', 'GOOG', 'GS', 'IBM', 'INTC', 'MS', 'NKE', 'NVDA']` is repeated verbatim in:
  - `config.py` line 21
  - `backend/main.py` line 33
  - `frontend/stock_sentiment_analysis/src/components/CustomSentiment/CustomSentiment.js` line 6 (unused `stocks` variable)
  - `frontend/stock_sentiment_analysis/src/components/SearchBar/SearchBar.js` lines 10–12
  - `backend/create_add_monthly_stock_data.py` line 82 (missing `IBM`)
- Impact: Ticker lists are inconsistent — `create_add_monthly_stock_data.py` omits `IBM`, creating a gap in historical stock data for that symbol. Any change to the supported ticker set must be made in 5 places.
- Fix approach: Define the canonical list once (e.g., in a backend config endpoint or a shared constants file), expose it via API, and have the frontend fetch it dynamically.

**Commented-out code left in production files:**
- Issue: Several blocks of commented-out code remain in production files.
  - `frontend/stock_sentiment_analysis/src/App.js` lines 12–14: old `StockDataProvider` + `HomePage` wiring
  - `backend/fetch_latest_news.py` lines 47–50: commented-out Lambda return block
  - `backend/create_add_monthly_stock_data.py` line 87: `create_table_and_push` call commented out
- Impact: Indicates unfinished refactoring and creates confusion about intent (are these meant to be restored?).
- Fix approach: Remove commented-out code; use git history if the old code needs to be recovered.

**`SentimentAnalysis.py` and `news_preprocess.py` are orphaned offline scripts:**
- Issue: Both files are data-processing scripts from an earlier pipeline that used AWS Comprehend and TextBlob. The current `main.py` uses FinBERT and Qwen instead.
- Files: `backend/SentimentAnalysis.py`, `backend/news_preprocess.py`
- Impact: Dead code in the `backend/` directory that gets included in the Docker image, adding confusion about the actual sentiment pipeline. `news_preprocess.py` also references `config.py`'s `file_path` which points to a non-existent local CSV.
- Fix approach: Move to an `archive/` or `scripts/` directory outside `backend/`, or delete if no longer needed.

**`CustomSentiment.js` declares an unused `stocks` constant:**
- Issue: `const stocks = ['AAPL', ...]` is declared at line 6 but never referenced in the component's JSX or logic.
- Files: `frontend/stock_sentiment_analysis/src/components/CustomSentiment/CustomSentiment.js` line 6
- Fix approach: Remove the unused constant.

**`TopBar.js` imports `BrowserRouter` but does not use it:**
- Issue: `BrowserRouter` is imported from `react-router-dom` but `TopBar` is already wrapped in a `Router` from `App.js` and never renders a second `BrowserRouter`.
- Files: `frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.js` line 4
- Fix approach: Remove the unused import.

**Dual Material UI versions installed simultaneously:**
- Issue: `package.json` includes both `@material-ui/core: ^4.12.4` (MUI v4) and `@mui/material: ^5.15.14` (MUI v5).
- Files: `frontend/stock_sentiment_analysis/package.json` lines 9, 11
- Impact: Doubles the Material UI bundle size shipped to users. Both versions have separate theming systems and will not share styles. The Docker build uses `--legacy-peer-deps` explicitly because of this conflict.
- Fix approach: Migrate all components to MUI v5 and remove `@material-ui/core`.

---

## Missing Error Handling

**`StockDataContext` silently swallows fetch failures:**
- Issue: If `getStockData()` fails, the error is logged to console but `stockData` remains `{}` and `stockArray` stays `[]`. No error state is exposed to consumers.
- Files: `frontend/stock_sentiment_analysis/src/context/StockDataContext.js` lines 11–14
- Impact: `StockChart` renders nothing. `TopCompanies` renders an empty list. `CompanyPage` shows "Stock not found" for every ticker. The user sees a blank page with no explanation.
- Fix approach: Add an `error` and `isLoading` value to the context so consumers can render appropriate error states.

**`CompanyPage` shows "Stock not found" when context is still loading:**
- Issue: If `stockData` context has not yet resolved (still fetching), `stock` will be `undefined` and the component immediately renders the "not found" error instead of a loading state.
- Files: `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js` lines 32–39
- Impact: On first load or slow connections, users navigating directly to `/company/AAPL` see a "not found" error that self-resolves, which is jarring and misleading.
- Fix approach: Add a separate `isLoading` flag to the context; render a skeleton/spinner in `CompanyPage` while data is in flight.

**`clean_time()` in `fetch_latest_news.py` lacks null guard:**
- Issue: `item['providerPublishTime']` is accessed without `.get()`, so any news item missing that key raises a `KeyError` that crashes the entire `main()` execution.
- Files: `backend/fetch_latest_news.py` line 14
- Impact: If any single news item lacks a publish timestamp, the entire S3 upload fails silently with a traceback. The equivalent function in `main.py` uses `.get()` correctly (line 153); this older script does not.
- Fix approach: Use `item.get('providerPublishTime')` with a fallback value, matching the pattern in `main.py`.

**`/analyze-custom` returns a raw exception string to the client:**
- Issue: The catch block on lines 278–279 returns `{"error": str(e)}`, exposing internal Python exception messages (including stack traces for some exception types) directly to the frontend.
- Files: `backend/main.py` lines 278–279
- Impact: Internal implementation details (model paths, library versions, system paths) can leak to any user.
- Fix approach: Log the full exception server-side; return a generic user-facing message with a request ID for correlation.

**No error boundary in the React app:**
- Issue: There is no React Error Boundary component anywhere in the component tree. A JavaScript runtime error in any component will crash the entire app to a blank screen.
- Files: `frontend/stock_sentiment_analysis/src/App.js`
- Fix approach: Wrap `<Routes>` (or individual route components) in an Error Boundary that renders a fallback UI.

---

## Incomplete Features / TODOs in Code

**`getCustomSentiment` uses HTTP GET with a large text payload:**
- Issue: The `/analyze-custom` endpoint is a `GET` request that passes the user's news text as a URL query parameter.
- Files: `frontend/stock_sentiment_analysis/src/components/CustomSentiment/CustomSentiment.js` line 16, `backend/main.py` line 258
- Impact: URL length limits (typically 2048–8192 characters depending on browser/server) cap the maximum input the user can analyze. Long articles will be silently truncated or cause a `414 URI Too Long` error. GET requests with sensitive payload also appear in server access logs and browser history.
- Fix approach: Change to `POST` with the text in the request body; update both the FastAPI route and the Axios call accordingly.

**`/news` endpoint uses a different Yahoo Finance API than `fetch_latest_news.py`:**
- Issue: `main.py` uses the Yahoo Finance search API (`query1.finance.yahoo.com/v1/finance/search`) which returns news as a side effect of a symbol search. The older `fetch_latest_news.py` used `yf.Ticker.get_news()`. The two approaches return different response shapes.
- Files: `backend/main.py` line 227, `backend/fetch_latest_news.py` line 25
- Impact: The `NewsItem` component already contains defensive fallback chains (`news.title || news.content?.title`) to handle both response shapes, indicating brittle API contract handling. Yahoo Finance's undocumented APIs change without warning.

**`CompanyPage` navigation label is misleading:**
- Issue: The company title renders as `{stock.name} Ticker` (e.g., "AAPL Ticker") because `stock.name` holds the ticker symbol, not the full company name.
- Files: `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js` line 49
- Impact: Poor UX — the heading reads "AAPL Ticker" instead of "Apple Inc." or simply "AAPL".
- Fix approach: Either fetch and store the full company name from yfinance (`stock.info['longName']`) alongside price data, or rewrite the label to not append "Ticker".

**App.test.js is the CRA default placeholder:**
- Issue: The only test file checks for a "learn react" link that does not exist in the actual app, so the test fails by design.
- Files: `frontend/stock_sentiment_analysis/src/App.test.js`
- Impact: Running `npm test` fails immediately. CI/CD that runs tests will always fail.
- Fix approach: Replace with a meaningful smoke test (e.g., render App and assert a known element renders).

---

## Dependency Risks

**`react-scripts 5.0.1` is end-of-life:**
- Issue: Create React App / `react-scripts` is no longer actively maintained. The last release was May 2022. Security vulnerabilities in underlying webpack/babel dependencies are no longer patched.
- Files: `frontend/stock_sentiment_analysis/package.json` line 17
- Impact: Known vulnerabilities in the build toolchain. No path to React 19 or modern bundler optimizations.
- Fix approach: Migrate to Vite (`@vitejs/plugin-react`) or Next.js. This is a significant migration but necessary for long-term security.

**`@material-ui/core 4.12.4` is several years behind current MUI:**
- Issue: MUI v4 reached end-of-life in September 2021. It is incompatible with React 18 StrictMode and has unresolved security advisories.
- Files: `frontend/stock_sentiment_analysis/package.json` line 9
- Fix approach: Remove entirely; use only MUI v5 (`@mui/material`).

**Python `requirements.txt` uses no version pins for critical packages:**
- Issue: `fastapi`, `uvicorn`, `pandas`, `yfinance`, `boto3`, `requests`, and `scipy` have no version pins. Only `transformers`, `accelerate`, and `bitsandbytes` have minimum version constraints.
- Files: `backend/requirements.txt`
- Impact: `pip install` on a fresh environment can install any version of FastAPI, yfinance, or boto3, including breaking major releases. Docker rebuilds are non-reproducible.
- Fix approach: Pin all dependencies to exact versions (`==`) or use a lockfile (`pip-compile` from `pip-tools`).

**`http` package in frontend dependencies is a security placeholder:**
- Issue: `"http": "^0.0.1-security"` is a stub package published by npm security to prevent dependency confusion attacks on the built-in Node.js `http` module. It provides no functionality.
- Files: `frontend/stock_sentiment_analysis/package.json` line 16
- Impact: Dead dependency that adds noise and confusion. Indicates someone attempted to `npm install http` thinking it was needed.
- Fix approach: Remove from `package.json` and `package-lock.json`.

**`aws-amplify` and `@aws-amplify/ui-react` are installed but appear unused:**
- Issue: The Amplify SDK packages are in `package.json` but no component imports from `aws-amplify` or `@aws-amplify/ui-react`. The `amplify/` directory exists with Amplify CLI scaffolding but no actual Amplify features (Auth, API, Storage) are configured.
- Files: `frontend/stock_sentiment_analysis/package.json` lines 6, 14; `frontend/stock_sentiment_analysis/amplify/backend/backend-config.json` (empty `{}`)
- Impact: ~400KB+ of unused JavaScript is bundled and shipped to users.
- Fix approach: Remove both packages if Amplify features are not actively used. If Amplify hosting is needed, the SDK is not required.

**`bitsandbytes` has no Windows support:**
- Issue: `bitsandbytes` is a quantization library with no official Windows binary. It is listed in `requirements.txt` but will fail to install on Windows environments.
- Files: `backend/requirements.txt` line 11
- Impact: Development on Windows requires WSL or Docker. The `backend/main.py` does not actually use `bitsandbytes` (no import), so this may be a leftover dependency.
- Fix approach: If not used, remove from `requirements.txt`. If quantization is planned, ensure deployment targets Linux only (documented).

---

## Architectural Risks

**Single-process backend cannot handle concurrent LLM requests:**
- Issue: Uvicorn is started with default settings (1 worker). Qwen2.5 inference is not async-safe and blocks the process during generation. There is no request queue, concurrency limit, or timeout.
- Files: `backend/main.py` line 284, `backend/Dockerfile` line 12
- Impact: A single slow `/analyze-custom` request starves all other requests. Two simultaneous users cause the second to wait for the first LLM call to complete before their request is even started.
- Fix approach: Separate the LLM inference service from the API server. Use a task queue (Celery + Redis, or RQ) with a dedicated worker process. The API server enqueues the job and polls or streams results.

**No model weight caching between Docker builds:**
- Issue: The Docker image does not mount or cache `~/.cache/huggingface`. Each `docker build` triggers a fresh model download (FinBERT ~440MB, Qwen2.5-1.5B ~3GB).
- Files: `backend/Dockerfile`, `docker-compose.yaml`
- Impact: CI/CD builds and container restarts take 10–30 minutes depending on network speed. This makes horizontal scaling via container orchestration extremely slow.
- Fix approach: Add a Docker volume for `/root/.cache/huggingface` in `docker-compose.yaml`. For production, bake model weights into a custom Docker image or use a shared model cache volume.

**`docker-compose.yaml` sets `REACT_APP_API_URL=http://localhost:8000` for the frontend container:**
- Issue: The frontend container runs Nginx; it cannot reach `localhost:8000` because `localhost` inside the frontend container refers to the Nginx process itself, not the backend service.
- Files: `docker-compose.yaml` line 25
- Impact: The frontend Docker container will always fall back to the hardcoded AWS API Gateway URL rather than the local backend, breaking the intended local development flow.
- Fix approach: Change the env var to `http://backend:8000` to use Docker Compose's internal DNS.

**No persistent storage for the backend cache:**
- Issue: All fetched stock and news data lives only in the Python process memory dict. Server restart, container restart, or Uvicorn reload clears all cached data.
- Files: `backend/main.py` lines 144–148
- Impact: Every cold start triggers expensive serial yfinance fetches (15 tickers) and news fetches (5 tickers) before the first response can be served.
- Fix approach: Use Redis (or even a simple SQLite file) for the cache layer so data survives restarts.

**Frontend has no loading state when the StockDataContext is empty:**
- Issue: `StockChart`, `TopCompanies`, and the ticker scrollbar all render from `StockDataContext`. While the API call is in flight, `stockArray` is `[]` — so all three sections render empty (no skeleton, no spinner).
- Files: `frontend/stock_sentiment_analysis/src/context/StockDataContext.js`, `frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.js`, `frontend/stock_sentiment_analysis/src/components/TopCompanies/TopCompanies.js`
- Fix approach: Add `isLoading: boolean` to the context value so components can render skeleton states.

---

## Scalability Concerns

**Yahoo Finance undocumented API dependency:**
- Issue: The news endpoint scrapes `query1.finance.yahoo.com/v1/finance/search` directly with a spoofed User-Agent. This is an undocumented, unauthenticated endpoint.
- Files: `backend/main.py` lines 215–228
- Impact: Yahoo Finance has rate-limited and blocked this endpoint in the past. Any structural change to the response JSON will silently return empty news. The system has no fallback news source.
- Fix approach: Use a documented news API (e.g., NewsAPI, Finnhub, Polygon.io) with proper rate limiting and API key management.

**In-memory cache is not shared across workers or instances:**
- Issue: The cache dict in `main.py` is process-local. If Uvicorn is ever started with multiple workers (`--workers 4`) or if multiple container replicas are deployed, each worker maintains its own independent cache, causing redundant fetches on every worker independently.
- Files: `backend/main.py` lines 144–148
- Impact: Linear increase in yfinance and Yahoo Finance API calls with each additional worker. Likely to trigger rate-limiting at scale.
- Fix approach: Replace in-process dict cache with Redis.

**Search bar supports only a closed list of 15 hardcoded tickers:**
- Issue: `SearchBar` presents a static `options` array. Users cannot search for any stock outside the predefined list, with no explanation of why.
- Files: `frontend/stock_sentiment_analysis/src/components/SearchBar/SearchBar.js` lines 10–12
- Impact: Severely limits product utility. The backend `yfinance` integration could theoretically handle any ticker symbol.
- Fix approach: Expose the ticker list from the backend API; allow free-text input with validation against yfinance on the backend.

---

*Concerns audit: 2026-03-26*
