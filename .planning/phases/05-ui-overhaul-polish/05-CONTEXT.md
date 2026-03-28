# Phase 5: UI Overhaul & Polish - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the flagship visual layer on top of the completed backend: a Recharts Treemap sentiment heatmap of all 100 stocks, a dual-axis price+sentiment ComposedChart on company detail pages, auto-refresh with skeleton loaders and error states, a fixed bottom ticker strip, and financial-grade typography polish. All frontend work — no backend changes unless a missing endpoint is discovered.

</domain>

<decisions>
## Implementation Decisions

### Homepage Layout
- **D-01:** The heatmap is the hero element at the top of the homepage — it replaces the current scrolling ticker strip in the main content area.
- **D-02:** The homepage vertical order is: Heatmap → Sector Sentiment summary row → Latest News feed.
- **D-03:** A fixed (sticky) horizontal ticker strip is pinned to the **bottom of the viewport** at all times — it remains visible while the user scrolls through the heatmap and news. Implemented as `position: fixed; bottom: 0` with `padding-bottom` added to the page body to prevent content from being obscured behind it.
- **D-04:** The existing `StockChart` scrolling component is repurposed/restyled into this fixed bottom bar. It shows ticker symbol, current price, and percent change for all 100 stocks in an auto-scrolling marquee.

### Heatmap — Sector Grouping & Excluded Sectors
- **D-05:** Stocks in sectors with `stock_count >= 3` are grouped under their GICS sector label (this is locked from Phase 4 / REQUIREMENTS.md UI-02).
- **D-06:** Stocks from sectors with `stock_count < 3` (Real Estate: EQIX, SPG; Materials: LIN — 3 stocks total) are grouped under an **"OTHER"** label at the end of the heatmap. All 100 stocks are visible; none are hidden.
- **D-07:** The "OTHER" group renders with the same cell styling as other sector groups but uses a neutral/muted label color to distinguish it from proper GICS sectors.

### Heatmap — Cell Sizing & Coloring
- **D-08:** Cells are sized by **market cap** using the `market_cap` field from `tickers.py` `TICKER_DATA` (this is locked per REQUIREMENTS.md UI-01 — "sized by market cap").
- **D-09:** Cell color uses the 5-stop diverging palette: strong positive `#16a34a` → positive `#4ade80` → neutral `#475569` → negative `#f87171` → strong negative `#dc2626`. Breakpoints at -1.0, -0.4, 0.0, +0.4, +1.0.
- **D-10:** The heatmap does **not** re-animate on every polling cycle — the Recharts `<Treemap>` data reference is updated in-place so cells transition color rather than re-rendering from scratch.

### Auto-Refresh & Settings
- **D-11:** Auto-refresh uses a `useInterval` custom hook. Polling pauses automatically when `document.visibilityState === 'hidden'` (browser tab hidden).
- **D-12:** A **settings gear icon** in the TopBar opens a MUI `<Dialog>` modal. The modal contains the refresh interval selector (options: 5 min / 10 min / 30 min; default 10 min). The modal is designed to accommodate additional settings in the future.
- **D-13:** During a refresh cycle: a 2px MUI `<LinearProgress>` bar appears at the very top of the page. The Last Updated timestamp swaps to "Updating…". No component unmounts/remounts.
- **D-14:** After refresh completes, the timestamp updates to "Last updated HH:MM" in 12-hour format.

### Company Detail Page
- **D-15:** The existing `CompanyPage.js` component is **retrofitted** (not rewritten). The missing `/stock/:ticker` route is added to `App.js`.
- **D-16:** The price chart is upgraded to a `<ComposedChart>`: price as `<Area>` on the left Y-axis, per-day sentiment bars as `<Bar>` with per-cell `<Cell>` coloring on the right Y-axis (domain fixed at -1 to 1). Bars colored green (`#4ade80`) for positive days, red (`#f87171`) for negative.
- **D-17:** The dual-axis chart remains mounted during background refresh — only data is updated, no unmount/remount cycle that would cause a blank flash.

### AI Narrative Staleness
- **D-18:** Below the Qwen narrative text on the company page, a small muted caption displays: "ℹ Generated X min ago" (computed from the `generated_at` timestamp in `narratives.json`). This is always visible when a narrative is present.
- **D-19:** When the narrative is in `pending` state (Qwen job queued), the section shows a MUI `<Skeleton animation="wave">` placeholder while polling for the result.

### Skeleton Loaders
- **D-20:** All data-dependent components show MUI `<Skeleton animation="wave">` while loading: metric cards, charts, heatmap, news feed. Skeleton height matches content height — no layout shift on data arrival.
- **D-21:** Dark theme skeleton: `bgcolor` overridden to `rgba(255,255,255,0.08)` so skeletons are visible against the dark glass background.

### Error States
- **D-22:** Each component shows its own inline error state (not a full-page error). Error state shows: which endpoint failed + a "Retry" button that re-triggers the fetch.
- **D-23:** Percent-change figures rendered as color-tinted pill badges: green background (`rgba(22,163,74,0.15)`) with green text for positive, red background (`rgba(220,38,38,0.15)`) with red text for negative. `font-variant-numeric: tabular-nums` applied to all price/change numbers.

### Typography & Polish
- **D-24:** Section labels use `text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.75rem` (financial-grade label convention).
- **D-25:** The existing dark glassmorphism CSS theme (`glass-panel`, `glass-card`) is preserved and extended — no visual identity change, only additions.

### Claude's Discretion
- Exact Recharts `<Treemap>` `content` render prop implementation for sector labels and cell coloring
- How `StockDataContext` is refactored to expose `{ data, loading, error, lastUpdated, refresh }` — implementation detail
- Tooltip design for heatmap cells (what info to show on hover)
- Mobile/tablet breakpoints for responsive layout (UI-08)
- Exact polling behavior when a refresh is already in-flight (skip or queue)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §UI — Core Dashboard (UI-01–UI-05) — exact specs for heatmap, dual-axis chart, auto-refresh
- `.planning/REQUIREMENTS.md` §UI — Polish & Quality (UI-06–UI-10) — skeleton, error states, responsive, typography, pill badges
- `.planning/ROADMAP.md` §Phase 5 — Success criteria (5 explicit acceptance conditions)

### Existing Frontend Code
- `frontend/stock_sentiment_analysis/src/App.js` — Current routes (missing `/stock/:ticker`), StockDataProvider wrapping
- `frontend/stock_sentiment_analysis/src/context/StockDataContext.js` — Current data fetch (no loading/error/refresh state — needs refactor)
- `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js` — Existing company detail page (retrofit target for dual-axis chart)
- `frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.js` — Current scrolling ticker (repurpose as fixed bottom bar)
- `frontend/stock_sentiment_analysis/src/components/HomePage/HomePage.js` — Current homepage layout (restructure target)
- `frontend/stock_sentiment_analysis/package.json` — MUI v5 only (`@mui/material ^5.15.14`), Recharts 2.12.3 — both already installed

### Backend Endpoints (Phase 4 deliverables — consume these)
- `GET /stocks` — All 100 stocks with price history; used for heatmap + ticker strip
- `GET /sentiment-trends?ticker=X&window=7d` — EMA sentiment time series per stock
- `GET /sector-sentiment` — Sector-level sentiment aggregates
- `GET /stock-narrative/{ticker}` — Qwen narrative; returns `{"status":"pending","job_id":"..."}` if not cached

### Data Structure
- `backend/tickers.py` — `TICKER_DATA` has `market_cap` per ticker (needed for Treemap cell sizing), `sector` for grouping

### State & Prior Context
- `.planning/STATE.md` §Research Flags — Qwen latency (30–120s), sector threshold edge cases
- `.planning/STATE.md` §Open Questions — Q3: dual-axis vs sub-panel (resolved: dual-axis per UI-03)

</canonical_refs>

<specifics>
## Specific Ideas

- Fixed bottom ticker: `position: fixed; bottom: 0; width: 100%; z-index: 1000` — add `padding-bottom: 48px` to `<body>` or page wrapper
- Settings modal: MUI `<Dialog>` with `<Select>` for interval — store selected interval in React state (or localStorage for persistence across reloads)
- Heatmap palette breakpoints: -1.0 → #dc2626, -0.4 → #f87171, 0.0 → #475569, +0.4 → #4ade80, +1.0 → #16a34a (linear interpolation between stops)
- "Generated X min ago" caption: derive from `generated_at` ISO string using `Math.floor((Date.now() - new Date(generated_at)) / 60000)` minutes
- `useInterval` hook: `useEffect` with `setInterval` inside, clears on unmount; wraps `document.addEventListener('visibilitychange', ...)` for tab-pause behavior
- Pill badge CSS: `border-radius: 9999px; padding: 2px 8px; font-variant-numeric: tabular-nums`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-ui-overhaul-polish*
*Context gathered: 2026-03-28*
