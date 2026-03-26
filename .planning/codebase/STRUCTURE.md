# Codebase Structure

**Analysis Date:** 2026-03-26

## Directory Layout

```
RealTime-Stock-Sentiment-Analysis-Engine/
├── backend/                          # FastAPI backend service
│   ├── Dockerfile                    # PyTorch CUDA base image, uvicorn entrypoint
│   ├── main.py                       # Entire backend: routes, models, cache, helpers
│   └── requirements.txt              # Python dependencies
│
├── frontend/
│   └── stock_sentiment_analysis/     # Create React App project root
│       ├── Dockerfile                # Multi-stage: Node build → Nginx serve
│       ├── package.json              # NPM manifest and scripts
│       ├── amplify/                  # AWS Amplify project scaffolding (currently empty config)
│       │   ├── .config/
│       │   ├── backend/
│       │   │   └── backend-config.json   # Empty — no Amplify categories configured
│       │   └── hooks/
│       ├── public/                   # Static HTML shell and assets
│       │   ├── index.html            # CRA HTML template, mounts #root div
│       │   ├── favicon.ico
│       │   └── manifest.json
│       └── src/                      # All React application source
│           ├── App.js                # Root component: router setup, StockDataProvider wrap
│           ├── App.css               # Global styles
│           ├── index.js              # ReactDOM.render entry point
│           ├── apis/
│           │   └── api.js            # Axios HTTP client: getStockData(), getNewsData()
│           ├── context/
│           │   └── StockDataContext.js   # Global stock price state via React Context
│           ├── utils/
│           │   └── getStockData.js   # Older/duplicate axios call (legacy, not used by context)
│           └── components/
│               ├── TopBar/           # Persistent nav: logo, SearchBar, route toggle
│               ├── SearchBar/        # MUI Autocomplete over 15 hardcoded ticker symbols
│               ├── HomePage/         # Layout: StockChart + NewsContent + Footer
│               ├── StockChart/       # Horizontal scrolling ticker strip
│               ├── StockDetails/     # Single ticker card (name, current, previous price)
│               ├── NewsContent/      # Layout wrapper around NewsData
│               ├── NewsData/         # Fetches and renders news feed + TopCompanies sidebar
│               ├── NewsItem/         # Leaf: article card with image + sentiment badge
│               ├── TopCompanies/     # Sorted ticker list sidebar using context data
│               ├── CompanyTicker/    # Single row: name, price, % change with color
│               ├── CompanyPage/      # Detail page: 1yr area chart, metrics, ticker news
│               ├── CustomSentiment/  # Page: text input → /analyze-custom → result card
│               └── Footer/           # Footer bar
│
├── config.py                         # Legacy root config (CSV dtypes, column names, symbols)
├── docker-compose.yaml               # Orchestrates backend:8000 + frontend:3000
├── test_output.json                  # Local test fixture / sample API response (200KB)
├── .gitignore
└── README.md
```

---

## Frontend Structure

**Entry Points:**
- `frontend/stock_sentiment_analysis/public/index.html` — HTML shell with `<div id="root">`
- `frontend/stock_sentiment_analysis/src/index.js` — ReactDOM mount point (standard CRA)
- `frontend/stock_sentiment_analysis/src/App.js` — Root React component; wraps everything in `StockDataProvider` and `BrowserRouter`, declares three routes

**Routes declared in `App.js`:**
| Path | Component |
|------|-----------|
| `/` | `HomePage` |
| `/custom-sentiment` | `CustomSentiment` |
| `/company/:ticker` | `CompanyPage` |

**`src/apis/`**
- `api.js` — The only authorized HTTP client module for frontend → backend calls. Exports `getStockData()` and `getNewsData(ticker?)`. URL resolution: `REACT_APP_API_URL` env var → hardcoded AWS Gateway fallback.
- `utils/getStockData.js` — Duplicate axios call to an older AWS API Gateway stage URL. Not imported by the active context or any component. Treat as dead code.

**`src/context/`**
- `StockDataContext.js` — Single context for global stock data. `StockDataProvider` wraps the app, calls `getStockData()` once on mount, exposes `stockArray` (normalized array) via context value. Components consume via `useContext(StockDataContext)`.

**`src/components/` — Component Inventory:**

Each component directory contains `ComponentName.js` and `ComponentName.css` (except `HomePage` and `NewsItem` which have no CSS file of their own).

| Component | Type | Data Source |
|-----------|------|-------------|
| `TopBar` | Layout/Nav | None (route-aware via `useLocation`) |
| `SearchBar` | Interactive | Hardcoded ticker list; navigates via `useNavigate` |
| `HomePage` | Page layout | None (composes children) |
| `StockChart` | Display | `StockDataContext` |
| `StockDetails` | Leaf display | Props from `StockChart` |
| `NewsContent` | Layout wrapper | None |
| `NewsData` | Data-fetching | `getNewsData()` via `api.js` |
| `NewsItem` | Leaf display | Props: news article object |
| `TopCompanies` | Display | `StockDataContext` |
| `CompanyTicker` | Leaf display | Props from `TopCompanies` |
| `CompanyPage` | Page + data-fetching | `StockDataContext` + `getNewsData(ticker)` |
| `CustomSentiment` | Page + data-fetching | Direct axios call to `/analyze-custom` |
| `Footer` | Layout | None |

---

## Backend Structure

The backend is a single-file service with no subdirectory module structure.

**`backend/main.py`** — Contains everything:
- FastAPI app instantiation and CORS middleware configuration
- Two ML model pipelines loaded at module import time:
  - `finbert_pipe` — `pipeline("sentiment-analysis", model="ProsusAI/finbert")`
  - `qwen_model` + `qwen_tokenizer` — `Qwen/Qwen2.5-1.5B-Instruct` via `AutoModelForCausalLM`
- In-memory `cache` dict (`stock_data`, `news` keys)
- Helper functions:
  - `finbert_score(text)` — returns float in [-1, 1]
  - `get_qwen_analysis(text)` — returns `(score, reason)` tuple
  - `analyze_sentiment_ensemble(text)` — calls `finbert_score` only (FinBERT-only ensemble for bulk)
  - `label_from_score(score)` — `> 0.15` → "Bullish", `< -0.15` → "Bearish", else "Neutral"
  - `clean_time(news)` — converts `providerPublishTime` Unix timestamps to formatted strings
- Route handlers: `get_stock_price()`, `get_news()`, `analyze_custom()`

**`backend/requirements.txt`** — Key dependencies:
- `fastapi`, `uvicorn` — web framework and ASGI server
- `yfinance` — Yahoo Finance price history wrapper
- `transformers>=4.45.0`, `accelerate>=0.34.0` — HuggingFace model loading
- `torch` (via Docker base image `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime`)
- `boto3` — listed but not actively called in `main.py` (legacy from AWS version)
- `textblob`, `nltk` — listed but not called in `main.py` (legacy)

**`backend/Dockerfile`:**
- Base: `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime`
- Installs Python deps, copies source, exposes port 8000
- Entrypoint: `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## Configuration Files and Their Purpose

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Defines `backend` (port 8000, optional GPU) and `frontend` (port 3000→80) services; sets `REACT_APP_API_URL=http://localhost:8000` for the frontend container |
| `backend/Dockerfile` | Backend container build: PyTorch CUDA base + pip install + uvicorn start |
| `frontend/stock_sentiment_analysis/Dockerfile` | Frontend build: Node 18 build stage (CRA) → Nginx alpine serve stage |
| `frontend/stock_sentiment_analysis/package.json` | NPM manifest; scripts: `start`, `build`, `test`, `eject`; lists React 18, react-router-dom v6, recharts, MUI v5, axios |
| `config.py` (root) | Legacy CSV configuration (column names, file path, symbols list). Not imported by the current backend. Artifact from the original data pipeline. |
| `frontend/stock_sentiment_analysis/amplify/backend/backend-config.json` | Empty JSON object `{}`. AWS Amplify scaffolding present but no categories configured. |
| `.gitignore` (root) | Standard ignores |

**Environment Variables:**
- `REACT_APP_API_URL` — Set on the frontend container via docker-compose. Controls which backend URL `api.js` and `CustomSentiment` use. If absent, code falls back to hardcoded AWS API Gateway URLs.
- `DEPLOYMENT_ENV` — Set to `local` on the backend container via docker-compose. Not read in `main.py` currently (informational only).

---

## Key Entry Points

**Starting the full stack:**
```bash
docker-compose up --build   # from repo root
```
- Backend available at: `http://localhost:8000`
- Backend Swagger docs at: `http://localhost:8000/docs`
- Frontend available at: `http://localhost:3000`

**Starting backend only (dev):**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Starting frontend only (dev):**
```bash
cd frontend/stock_sentiment_analysis
REACT_APP_API_URL=http://localhost:8000 npm start
```

**React application root:**
- `frontend/stock_sentiment_analysis/src/index.js` → mounts `<App />` into `#root`
- `frontend/stock_sentiment_analysis/src/App.js` → declares routing and context wrapping

**Backend application root:**
- `backend/main.py` → `app = FastAPI()` at module level; `uvicorn main:app` as entrypoint

---

## Where to Add New Code

**New API endpoint:**
- Add route handler directly to `backend/main.py`
- Follow the existing pattern: `@app.get("/route-name")` with an `async def` or sync `def`

**New frontend page/route:**
- Create `src/components/NewPage/NewPage.js` and `NewPage.css`
- Add a `<Route path="/new-path" element={<NewPage />} />` in `src/App.js`
- Add a navigation link in `src/components/TopBar/TopBar.js` if needed

**New API call from frontend:**
- Add the function to `src/apis/api.js` following the `getStockData` / `getNewsData` pattern (axios + env var URL resolution)
- Do not add raw axios calls inside components (except `CustomSentiment` which currently does so directly)

**New reusable display component:**
- Create `src/components/ComponentName/ComponentName.js` + `ComponentName.css`
- Components that need global stock data: use `useContext(StockDataContext)`
- Components that fetch their own data: use local `useState` + `useEffect` pattern matching `NewsData.js`

---

*Structure analysis: 2026-03-26*
