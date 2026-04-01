# RealTime Stock Sentiment Analysis Engine

**Status: v1.0 Complete** ✅

A professional stock research dashboard powered by FinBERT sentiment analysis and AI narratives. Features a real-time sentiment heatmap across 100 S&P equities, sector aggregations, EMA trend analysis, and auto-refreshing price/sentiment dual-axis charts—all with a modern fintech UI.

**Key Features:**
- 📊 Sentiment heatmap of 100 S&P stocks grouped by GICS sector
- 📈 Dual-axis price/sentiment charts with per-day sentiment bars
- 🧠 FinBERT full-probability scoring with confidence-weighted aggregation
- ✍️ Qwen-powered AI research narratives for each stock
- 🔄 Auto-refresh every 10 minutes with visible last-updated timestamp
- 🌓 Dark/light theme toggle with CSS variable design system
- ⚡ Non-blocking async architecture with TTL caching

---

## Running with Docker

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Ports `8000` (backend) and `3000` (frontend) free

---

### Start the app

```bash
docker compose up --build
```

- `--build` rebuilds images from source — required on first run or after code changes
- Backend starts at `http://localhost:8000`
- Frontend starts at `http://localhost:3000`

To run in detached mode (background):

```bash
docker compose up --build -d
```

---

### Stop the app

Stop containers and remove them (preserves built images):

```bash
docker compose down
```

Stop and also remove built images (forces a full rebuild next time):

```bash
docker compose down --rmi all
```

---

### Full restart (down then up)

```bash
docker compose down && docker compose up --build
```

Or in detached mode:

```bash
docker compose down && docker compose up --build -d
```

---

### View logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend
```

---

---

## Architecture

### Backend (FastAPI + ML)
- **Async event loop**: Non-blocking model loading, TTL-based caching, parallel yfinance calls
- **FinBERT sentiment scoring**: Full-probability distribution (positive/neutral/negative) with confidence weighting
- **Job queue**: Async background Qwen narrative generation with polling endpoint
- **Data pipeline**: Batched yfinance with tiered news rotation across 100 S&P stocks

### Frontend (React 18)
- **Modern design**: CSS custom properties, dark/light theme toggle, glassmorphism-free styling
- **Recharts visualizations**: Sentiment heatmap (Treemap), dual-axis chart (ComposedChart)
- **State management**: StockDataContext with auto-refresh, visibility guards, localStorage persistence
- **Responsive layout**: Skeleton loaders during data fetch, graceful error states

### Deployment
- **Docker Compose**: Containerized backend + frontend for consistent local/cloud environments
- **Nginx reverse proxy**: Optional frontend static serving (nginx.conf included)
- **GPU support**: CUDA 12.8 optional for ML model acceleration (see below)

---

## Services

| Service  | URL                      | Description              |
|----------|--------------------------|--------------------------|
| Frontend | http://localhost:3000    | React dashboard          |
| Backend  | http://localhost:8000    | FastAPI + FinBERT models |
| API docs | http://localhost:8000/docs | Auto-generated Swagger  |

---

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stock-price` | GET | OHLC data + sector grouping for all 100 tickers |
| `/sentiment-trends` | GET | EMA-smoothed sentiment time series |
| `/sector-sentiment` | GET | Aggregated sentiment by GICS sector |
| `/stock-narrative/{ticker}` | GET | AI-generated narrative (Qwen) |
| `/analyze-custom` | POST | Custom text sentiment analysis (API key required) |

---

## GPU support (optional)

The backend Dockerfile includes CUDA 12.8 support for RTX 5060 / Blackwell GPUs. GPU is disabled by default. To enable it, uncomment the `deploy` block in `docker-compose.yaml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on the host.

---

## Future Work

Backlog items captured for post-v1.0 roadmap:
- **Microservices Architecture** (Phase 7): Split monolithic backend into api/sentiment/narrative containers
- **Database Implementation** (999.1): Replace in-memory storage with PostgreSQL/MongoDB
- **Custom Sentiment Page** (999.2): User-facing interface for sentiment submission

See [ROADMAP.md](.planning/ROADMAP.md) for full phase breakdown.

---

*v1.0 completed: 2026-03-30*
