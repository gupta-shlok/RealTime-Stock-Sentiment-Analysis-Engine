# RealTime Stock Sentiment Analysis Engine

A real-time stock sentiment dashboard powered by NLP, featuring a sentiment heatmap, sector sentiment cards, AI-generated stock narratives, and a live scrolling ticker strip.

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

### GPU support (optional)

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

## Services

| Service  | URL                      | Description              |
|----------|--------------------------|--------------------------|
| Frontend | http://localhost:3000    | React dashboard          |
| Backend  | http://localhost:8000    | FastAPI + sentiment model |
| API docs | http://localhost:8000/docs | Auto-generated Swagger  |
