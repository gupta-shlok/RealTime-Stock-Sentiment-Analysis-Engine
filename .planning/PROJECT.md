# RealTime Stock Sentiment Analysis Engine

## What This Is

An AI-powered stock research tool that surfaces sentiment insights across the top 100 US equities. It combines real-time price charts, FinBERT-powered sentiment scoring on live news, a visual sentiment heatmap, and LLM-generated research summaries — all in a polished, production-quality React dashboard backed by a FastAPI + ML inference pipeline.

## Core Value

A recruiter or engineer who opens this app should immediately see what makes stocks move — sentiment + price in one view — before they've read a single line of code.

## Requirements

### Validated

- ✓ Stock price history (OHLC) fetched via yfinance for a set of tickers — existing
- ✓ News feed with FinBERT sentiment scoring per article — existing
- ✓ Custom text sentiment analysis endpoint (FinBERT + Qwen2.5 ensemble) — existing
- ✓ React SPA with routing, stock detail pages — existing
- ✓ Docker Compose local deployment (backend + frontend) — existing

### Validated

- ✓ Security hardening — credentials removed, CORS restricted, API key auth, input validation — Validated in Phase 1: Security & Cleanup
- ✓ Performance fixes — async model loading, TTL cache, non-blocking yfinance, background LLM inference — Validated in Phase 2: Backend Performance
- ✓ Expand ticker coverage from 15 to top 100 US stocks with sector grouping — Validated in Phase 3: Data Pipeline Expansion
- ✓ Sentiment trend over time — EMA-smoothed score time series via /sentiment-trends — Validated in Phase 4: Sentiment Intelligence Upgrade
- ✓ Sector-level sentiment aggregation — /sector-sentiment with stock_count >= 3 gate — Validated in Phase 4: Sentiment Intelligence Upgrade
- ✓ Richer AI insights — per-stock Qwen narrative via /stock-narrative/{ticker} with job queue — Validated in Phase 4: Sentiment Intelligence Upgrade
- ✓ FinBERT full-probability scoring — confidence-weighted aggregation, 35-day persistent scores — Validated in Phase 4: Sentiment Intelligence Upgrade

### V1.0 Complete

- ✓ Sentiment heatmap — grid of all 100 stocks color-coded by current sentiment score (Phase 5)
- ✓ Auto-refresh with visible last-updated timestamp (10 min polling with visibility guard) (Phase 5)
- ✓ UI polish — skeleton loaders, proper error states, responsive layout, cohesive visual design (Phase 5)
- ✓ Visual design overhaul — dark design system, CSS variables, modern typography (Inter font), theme toggle (Phase 6)

### Out of Scope

- Open-ended ticker search — scope too large; top 100 is the right portfolio boundary
- User accounts / authentication — adds complexity without portfolio value
- True real-time WebSocket streaming — TTL-based polling is sufficient
- Trading or order execution — purely a research/analysis tool
- Mobile native app — responsive web is sufficient

## Context

This is a brownfield project. The core architecture (React SPA → FastAPI → HuggingFace models) is sound and will be preserved. The primary work is: (1) fixing production-blocking issues the codebase audit surfaced, (2) scaling the data layer, and (3) adding the visual features that make the portfolio story compelling.

**Existing issues to address (from codebase audit):**
- CRITICAL: AWS credentials hardcoded in `backend/fetch_latest_news.py` — must rotate and move to env vars
- `team-provider-info.json` committed with AWS account ID and IAM ARNs
- Wildcard CORS (`allow_origins=["*"]`) on public API
- No auth on any endpoint — `/analyze-custom` especially exploitable (LLM on every call)
- ML models loaded synchronously at module import (blocks server startup)
- In-memory cache has no TTL — data goes stale immediately
- yfinance calls are synchronous and block the async event loop
- MUI v4 + v5 co-installed (requires `--legacy-peer-deps`); should consolidate to v5

## Constraints

- **Tech stack**: Keep React 18 + FastAPI + FinBERT + Qwen2.5 — these are the portfolio story, not just implementation details
- **Scale**: Top 100 tickers only — open-ended search is out of scope
- **Deployment**: Docker Compose for local; production target is a single cloud host (not microservices)
- **Data source**: yfinance + Yahoo Finance news API (free tier) — no paid data subscriptions

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Top 100 tickers (not open-ended search) | Right scale for portfolio; open-ended requires search infra | ✓ Implemented Phase 3 |
| Sentiment heatmap as flagship visual | Immediately communicates value; shows scale of 100 stocks | — Phase 5 |
| TTL cache + polling instead of WebSockets | Simpler, sufficient for portfolio; real-time adds infra complexity | ✓ Implemented Phase 2 |
| Keep FinBERT + Qwen2.5 ensemble | Core AI differentiator; already implemented | ✓ Upgraded Phase 4 |
| Consolidate to MUI v5 only | Remove `--legacy-peer-deps` hack; cleaner dependency tree | — Phase 5 |
| finbert_score() returns (score, confidence) tuple | Full-probability scoring; confidence drives weighted aggregation | ✓ Locked Phase 4 |
| FINBERT_MIN_CONFIDENCE = 0.55 | Filters near-neutral noise from daily aggregates | ✓ Locked Phase 4 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 — v1.0 complete (Phases 1–6 delivered)*
*Next milestone: v1.1 (Phases 7–8) — Microservices Architecture + Automated Test Suite*
