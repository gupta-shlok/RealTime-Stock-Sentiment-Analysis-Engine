---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 5
current_plan: 2 (next)
status: verifying
stopped_at: Completed 06-01-PLAN.md
last_updated: "2026-03-30T11:42:05.210Z"
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 17
  completed_plans: 14
---

# Project State: RealTime Stock Sentiment Analysis Engine

**Last updated:** 2026-03-28
**Project reference:** `.planning/PROJECT.md`
**Requirements reference:** `.planning/REQUIREMENTS.md`
**Roadmap reference:** `.planning/ROADMAP.md`

---

## Core Value

A recruiter or engineer who opens this app immediately sees what makes stocks move — sentiment + price in one view — before reading a single line of code.

---

## Current Position

Phase: 05 (ui-overhaul-polish) — IN PROGRESS
Plan: 3 of 3 complete
**Milestone:** v1.0
**Current phase:** 5
**Current plan:** 2 (next)
**Status:** Phase complete — ready for verification

**Progress bar:**

```
Phase 1 [██████████] 100%   Security & Cleanup
Phase 2 [██████████] 100%   Backend Performance
Phase 3 [██████████] 100%   Data Pipeline Expansion
Phase 4 [██████████] 100%   Sentiment Intelligence Upgrade (3/3 plans done)
Phase 5 [████░░░░░░] 77%    UI Overhaul & Polish (1/3 plans done)
```

---

## Phase Summary

| Phase | Name | Requirements | Status | Completed |
|-------|------|--------------|--------|-----------|
| 1 | Security & Cleanup | SEC-01–06, CLEAN-01–04 (10 total) | ✅ Complete | 2026-03-27 |
| 2 | Backend Performance | PERF-01–05 (5 total) | ✅ Complete | 2026-03-28 |
| 3 | Data Pipeline Expansion | DATA-01–04 (4 total) | ✅ Complete | 2026-03-28 |
| 4 | Sentiment Intelligence Upgrade | SENT-01–05 (5 total) | ✅ Complete | 2026-03-28 |
| 5 | UI Overhaul & Polish | UI-01–10 (10 total) | Pending | - |

**Total v1 requirements:** 34 / 34 mapped

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete | 4 / 5 (Phase 5 pending) |
| Requirements complete | 24 / 34 (SENT-01–05 complete) |
| Plans written | 9 |
| Plans complete | 9 |
| Phase 04 P01 duration | 3 min, 2 tasks, 7 files |
| Phase 04 P02 duration | 8 min, 2 tasks, 5 files |
| Phase 04 P03 duration | 7 min, 2 tasks, 2 files |
| Phase 05 P01 | 5 min | 3 tasks | 3 files |
| Phase 05-ui-overhaul-polish P03 | 2 min | 2 tasks | 3 files |
| Phase 05 P02 | 8 min | 2 tasks | 6 files |
| Phase 05 P04 | 5 min | 3 tasks | 10 files |
| Phase 06 P01 | 1 min | 3 tasks | 4 files |

## Accumulated Context

### Roadmap Evolution

- Phase 6 added: Visual design overhaul — dark design system, CSS variables, glassmorphism, TopBar redesign, news layout, typography scale, consistent component styling across all pages (added 2026-03-30 after Phase 5 UAT revealed the UI looks dated despite correct components)
- Phase 7 added: Microservices architecture — split backend into api/sentiment/narrative containers so ML models never restart on frontend/api changes (added 2026-03-30)
- Phase 8 added: Automated test suite — React Testing Library frontend tests, pytest backend unit + integration tests, GitHub Actions CI pipeline to replace manual UAT (added 2026-03-30)

### Key Decisions Locked

| Decision | Rationale |
|----------|-----------|
| 5-phase linear dependency chain | Security must precede async refactor; async must precede ticker expansion; ticker expansion must precede sentiment math; all backend must precede UI |
| CLEAN-01–04 assigned to Phase 1 alongside SEC-01–06 | Both are remediation of existing defects, not new features; combining them avoids a separate "housekeeping" phase |
| Phase 5 is the only UI phase | All frontend work blocked on backend endpoints from Phases 3–4; building UI earlier requires mocking that must be undone |
| Phase 5 Plan 01: useInterval holds no in-flight guard | Caller's responsibility via isRefreshingRef in StockDataProvider — keeps hook general-purpose |
| Phase 5 Plan 01: loading vs isRefreshing distinction | loading=true only on first fetch (no data yet); isRefreshing=true during background polling — consumers show skeleton vs progress bar |
| Phase 5 Plan 01: refreshInterval persisted to localStorage | Key: sentiment_refresh_interval; default 600000ms (10 min); options 300000/600000/1800000 |
| Granularity: Standard (5 phases) | 34 requirements across 6 categories compresses naturally to 5 delivery boundaries at standard granularity |
| Phase 4 Plan 01: All stub tests use pytest.skip() (not xfail) | Suite stays always green; accidental skip removal causes immediate failure rather than silent pass |
| Phase 4 Plan 01: Session-scoped fixtures for torch mock tensors | Avoids re-creating torch tensors per test function for performance |
| Phase 4 Plan 02: finbert_score() returns (score, confidence) tuple | All callers must unpack; score=P(pos)-P(neg) in [-1,1], confidence=max(softmax); breaking change from old float return |
| Phase 4 Plan 02: aggregate_daily_score() returns None not 0.0 for no-data days | Distinguishes "no articles passed threshold" from "truly neutral" — Plan 03 trend endpoints must check for None |
| Phase 4 Plan 03: WINDOW_TO_SPAN maps 7d->span=5, 30d->span=20; invalid window is HTTP 400 | Invalid window is a client error, not a missing-data scenario — consistent with REST conventions |
| Phase 4 Plan 03: sector-sentiment stock_count counts tickers WITH data; Real Estate (EQIX+SPG=2) always excluded | Exclusion is structural (only 2 tickers in tickers.py), not data-dependent |
| Phase 4 Plan 03: qwen_worker branches on job.get("type","analyze") defaulting to analyze-custom | Zero regression risk for existing /analyze-custom callers; "narrative" path writes to NARRATIVES_FILE |

### Critical Pre-Phase Notes

- **Before Phase 1:** Rotate AWS credentials immediately if the repo is or will be made public — git history is permanent even after removal
- **Before Phase 2:** Measure Qwen2.5-1.5B CPU tokens/second on the host machine during warm-up; if below 1 t/s, reduce `max_new_tokens` to 150 for narratives
- **Before Phase 3:** Verify current S&P 100 constituents against the official S&P Dow Jones factsheet — GEV and PLTR were added in 2024 and the list changes periodically
- **Before Phase 4:** After implementing full-probability FinBERT scoring, run against the real news feed and check neutral rate; if > 60%, apply the confidence-threshold override rule
- **Before Phase 5:** Confirm all Phase 4 API endpoints (`/sentiment-trends`, `/stock-narrative/{ticker}`, `/sector-sentiment`, `/health`) are returning real data before building UI against them

### Research Flags (Medium/Low Confidence — Validate During Implementation)

- **Qwen job queue (Phase 4):** `asyncio.Queue` has no persistence. If the server restarts mid-job, queued results are lost. Decide whether to add a simple file-based checkpoint or accept this limitation at portfolio scope.
- **Qwen narrative latency (Phase 4):** Documented as 30-120s on CPU. Measure actual latency before choosing `max_new_tokens=250`; if over 3 minutes, rethink the polling UX interval.
- **Yahoo Finance rate limits (Phase 3):** No official documentation. The 2-chunk + 1.5s delay strategy is conservative but may still hit 429s on concurrent cache misses. Monitor during testing.
- **Sector display thresholds (Phase 4/5):** With 102 tickers, Energy (3), Real Estate (2), Utilities (3), Materials (1) may fall at or below the `stock_count >= 3` gate. Decide whether to show partial sectors with a caveat or suppress them entirely.
- **UUID deduplication stability (Phase 3):** Validate that Yahoo Finance assigns stable UUIDs to the same article across repeated calls before relying on UUID-based deduplication for all 100 tickers.

### Open Questions (Unresolved)

1. Should `/stock-price` and `/news` be gated with API key auth, or remain public for portfolio reviewers? Research recommends public with rate limiting.
2. Should the heatmap use equal cell sizing (easier, ships faster) or market-cap-proportional sizing (more informative, requires additional yfinance call for volume/market cap data)?
3. Dual-axis overlay vs. separate sub-panel for the price+sentiment chart — dual-axis is the current spec (UI-03) but separate panels are cleaner at longer time windows.

---

## Blockers

None at roadmap creation. No phase has started.

---

## Session Continuity

**To resume work:**

1. Check phase status in this file
2. Read `.planning/ROADMAP.md` for the current phase goal and success criteria
3. Read `.planning/REQUIREMENTS.md` for the specific requirement IDs in scope
4. Run `/gsd:plan-phase <N>` to generate a detailed execution plan for the next phase

**Last session:** 2026-03-30T11:42:05.206Z
**Stopped at:** Completed 06-01-PLAN.md
**Next action:** Phase 05 Plan 02 — UI components (heatmap, ticker strip, skeleton loaders)

---

*State initialized: 2026-03-26*
*Milestone: v1.0*
