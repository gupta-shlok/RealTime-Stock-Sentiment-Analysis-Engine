# Technology Stack

**Analysis Date:** 2026-03-26

## Languages

**Primary:**
- Python 3.x - Backend API, ML inference, data preprocessing, AWS utility scripts
- JavaScript (ES2020+) - React frontend, API client, utility functions

**Secondary:**
- CSS3 - Component-level styling (co-located `.css` files per component)
- HTML5 - `public/index.html` shell for the React SPA

## Runtime

**Backend:**
- Python (exact version pinned by the PyTorch base image: `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime`)
- CUDA 12.6 / cuDNN 9 available inside the Docker image for GPU-accelerated inference

**Frontend:**
- Node.js 18 (Alpine) — used only during Docker build stage; runtime is Nginx
- Browser target: last 1 Chrome / Firefox / Safari (dev), >0.2% market share (prod)

**Package Managers:**
- `npm` — frontend (`package-lock.json` present; `--legacy-peer-deps` required due to MUI v4/v5 co-installation)
- `pip` — backend (no lockfile; `requirements.txt` pins ranges or no versions)

## Frameworks

**Backend:**
- `fastapi` (unpinned) — HTTP API framework; exposes `/stock-price`, `/news`, `/analyze-custom`
- `uvicorn` (unpinned) — ASGI server; entry point `uvicorn main:app --host 0.0.0.0 --port 8000`

**Frontend:**
- `react` ^18.2.0 — UI framework
- `react-dom` ^18.2.0 — DOM renderer
- `react-router-dom` ^6.22.3 — client-side routing (`BrowserRouter`, `Routes`, `Route`, `useParams`)
- `react-scripts` 5.0.1 — CRA build toolchain (webpack, Babel, Jest, ESLint bundled)

## Key Dependencies

**ML / NLP (Backend):**
- `transformers` >=4.45.0 — Hugging Face Transformers; loads `ProsusAI/finbert` (sentiment pipeline) and `Qwen/Qwen2.5-1.5B-Instruct` (causal LM)
- `accelerate` >=0.34.0 — enables `device_map="auto"` for model sharding across CPU/GPU
- `bitsandbytes` >=0.45.0 — quantization support for Qwen on CUDA
- `scipy` (unpinned) — numerical dependency pulled in by ML libraries
- `textblob` (unpinned) — used in `news_preprocess.py` for legacy polarity-based sentiment scoring
- `nltk` (unpinned) — tokenization, stopword removal, lemmatization in `news_preprocess.py`
- `torch` — bundled inside `pytorch/pytorch:2.6.0` base image; used directly in `main.py` for `torch.cuda.is_available()`, `torch.no_grad()`, dtype selection

**Data / Finance (Backend):**
- `yfinance` (unpinned) — Yahoo Finance data fetching (`Ticker.history()`, `Ticker.get_news()`)
- `pandas` (unpinned) — DataFrame operations, CSV chunked reading, monthly aggregation
- `requests` (unpinned) — HTTP calls to `query1.finance.yahoo.com` for news search endpoint

**AWS (Backend):**
- `boto3` (unpinned) — AWS SDK; used for S3 (`put_object`), DynamoDB (`resource`, `client`), and Comprehend (`detect_sentiment`) in utility/legacy scripts

**Frontend UI:**
- `recharts` ^2.12.3 — charting; `AreaChart`, `LineChart`, `ResponsiveContainer` used in `CompanyPage.js` and other components
- `@mui/material` ^5.15.14 — Material UI v5 component library
- `@material-ui/core` ^4.12.4 — Material UI v4 (legacy; co-installed alongside v5, requires `--legacy-peer-deps`)
- `@emotion/react` ^11.11.4 — CSS-in-JS runtime for MUI v5
- `@emotion/styled` ^11.11.5 — styled-component wrapper for MUI v5
- `axios` ^1.6.8 — HTTP client for all backend API calls from the frontend
- `aws-amplify` ^6.0.21 — AWS Amplify JS SDK (imported but Amplify backend resources are currently empty; `backend-config.json` is `{}`)
- `@aws-amplify/ui-react` ^6.1.6 — Amplify React UI components

**Utilities:**
- `python-dotenv` (unpinned) — loads `.env` in `main.py` via `load_dotenv()`
- `web-vitals` ^2.1.4 — CWV reporting in `reportWebVitals.js`
- `http` ^0.0.1-security — placeholder package (no-op; listed in dependencies but provides nothing)

## Build Tools

**Frontend:**
- `react-scripts` 5.0.1 — wraps webpack 5, Babel 7, PostCSS; zero-config CRA build
- `npm run build` → outputs to `frontend/stock_sentiment_analysis/build/`
- `npm run start` → dev server on port 3000

**Backend:**
- No build step; Python source files run directly via `uvicorn`

**Linting / Formatting:**
- ESLint — configured via `eslintConfig` in `package.json`; extends `react-app` and `react-app/jest`
- No Prettier config detected
- No Python linter config detected (no `.flake8`, `pyproject.toml`, or `setup.cfg`)

## Testing

**Frontend:**
- `@testing-library/react` ^13.4.0 — React component testing
- `@testing-library/jest-dom` ^5.17.0 — custom Jest matchers
- `@testing-library/user-event` ^13.5.0 — user interaction simulation
- Jest — bundled inside `react-scripts`; run via `npm test`
- Only one test file present: `src/App.test.js`

**Backend:**
- No test framework or test files detected

## Deployment / Containerization

**Docker:**
- `backend/Dockerfile` — base image `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime`; installs pip deps; exposes port 8000; runs `uvicorn`
- `frontend/stock_sentiment_analysis/Dockerfile` — multi-stage: Node 18 Alpine build stage → Nginx Alpine production stage; serves static build on port 80
- `docker-compose.yaml` — orchestrates both services; backend on `0.0.0.0:8000`, frontend on `0.0.0.0:3000` (mapped to Nginx 80); requires NVIDIA GPU driver on host (`driver: nvidia`, `count: 1`)

**AWS Amplify (Frontend Hosting):**
- `amplify.yml` at repo root defines build pipeline: `npm ci` + `npm run build`; artifact base `build/`
- Amplify project name: `stocksentimentanalys`; provider: `awscloudformation`
- Amplify CLI config present but backend resources are empty (no auth, API, or storage categories provisioned)

**AWS API Gateway (Backend Hosting - Production):**
- Production API endpoints are hardcoded fallbacks in the frontend:
  - `https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/stock-price` (`src/apis/api.js`)
  - `https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/news` (`src/apis/api.js`)
  - `https://ip8z0jodq4.execute-api.us-east-1.amazonaws.com/test/stock-price` (`src/utils/getStockData.js` — older utility, appears superseded by `src/apis/api.js`)

---

*Stack analysis: 2026-03-26*
