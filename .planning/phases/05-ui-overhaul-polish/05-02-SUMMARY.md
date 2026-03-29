---
phase: 05-ui-overhaul-polish
plan: 02
subsystem: frontend/components
tags: [react, recharts, treemap, sentiment, heatmap, mui, homepage]
dependency_graph:
  requires:
    - 05-01 (StockDataContext with stocks array, getSectorSentiment in api.js)
  provides:
    - SentimentHeatmap component (Recharts Treemap, 5-stop diverging palette, stable ref anti-animation)
    - SectorSentimentRow component (sector sentiment cards, loading skeleton, error+Retry)
    - Restructured HomePage (Heatmap -> SectorSentimentRow -> NewsContent vertical order)
  affects:
    - frontend/stock_sentiment_analysis/src/components/HomePage/HomePage.js (rewritten — old StockChart+Footer removed)
tech_stack:
  added: []
  patterns:
    - treeDataRef.current.splice mutation to prevent Recharts re-animation on polling updates
    - useMemo with external ref for stable array reference across re-renders
    - Linear color interpolation (lerpColor) for 5-stop diverging sentiment palette
    - FEW_STOCK_TICKERS set for grouping small-sector tickers under OTHER
key_files:
  created:
    - frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.js
    - frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.css
    - frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.js
    - frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.css
    - frontend/stock_sentiment_analysis/src/components/HomePage/HomePage.css
  modified:
    - frontend/stock_sentiment_analysis/src/components/HomePage/HomePage.js
decisions:
  - "FEW_STOCK_TICKERS hardcoded as Set(['EQIX','SPG','LIN']) — matches tickers.py sectors with stock_count < 3; simpler than dynamic threshold"
  - "treeDataRef.splice mutation pattern chosen over keying by stable ID — Recharts Treemap re-animates on new array reference regardless of key prop"
  - "SectorSentimentRow getSentimentColor uses flat threshold bands (not lerp) — sector cards show a definitive color signal, not a gradient"
  - "HomePage removes StockChart and Footer imports — StockChart moved to CompanyPage (plan 05-03); Footer removal is intentional per UI-SPEC"
metrics:
  duration: "~8 min"
  completed: "2026-03-29"
  tasks: 2
  files: 6
---

# Phase 05 Plan 02: Heatmap Hero & Sector Row Summary

**One-liner:** Recharts Treemap sentiment heatmap with 5-stop diverging palette and in-place array mutation for stable re-render, plus MUI-skeleton-backed sector sentiment row and restructured homepage hero layout.

---

## What Was Built

### Task 1 — SentimentHeatmap.js + SentimentHeatmap.css (commit eb62fe6)

Created `frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.js`.

**Color system:** `lerpColor` interpolates between adjacent hex stops. `getSentimentColor` maps the score range [-1, +1] across 4 linear segments using the 5-stop diverging palette: `#dc2626` (strong negative) → `#f87171` → `#475569` (neutral) → `#4ade80` → `#16a34a` (strong positive). Null/undefined scores default to neutral `#475569`.

**Data builder:** `buildTreemapData` groups stocks into sector buckets. Stocks whose ticker appears in `FEW_STOCK_TICKERS = new Set(['EQIX', 'SPG', 'LIN'])` (Real Estate 2-stock sector + Materials 1-stock sector) are routed to an `OTHER` group instead, matching the backend `stock_count >= 3` gate.

**Anti-animation pattern:** `treeDataRef` holds the first-built array. On subsequent `stocks` changes, `treeDataRef.current.splice(0, length, ...newData)` mutates the array in-place. `useMemo` returns the same object reference, so Recharts sees no new array and skips entry animation. `isAnimationActive={false}` is also set on the `<Treemap>` element as a belt-and-suspenders guard.

**CustomTreemapContent:** Depth-0 nodes (sectors) render a text label in `#94a3b8` (or `#64748b` for OTHER). Depth-1 nodes render a colored `<rect>` with `getSentimentColor(sentiment)` fill and a ticker `<text>` when `width > 40`.

**Tooltip:** Shows ticker, price, sentiment score with sign prefix, and percent_change badge. Sector-level nodes are filtered (`if d.children return null`).

**States:** Loading renders a pulsing skeleton at 400px height. Error and empty states show centered messages.

### Task 2 — SectorSentimentRow.js + restructured HomePage.js (commit b800f61)

**SectorSentimentRow** fetches `/sector-sentiment` via `getSectorSentiment()` in a `useEffect` on mount. Loading state renders 5 MUI `<Skeleton>` rectangles at 80px height. Error state shows the message plus an outlined MUI `<Button>` labeled "Retry" that re-calls `fetchSectors`. Success state renders one `glass-card` div per sector with: sector name (`section-label`), `avg_score` formatted with sign prefix (`sector-score` colored by `getSentimentColor`), and stock count (`sector-count`).

**Homepage restructure:** Removed old `StockChart`, `TopBar`, and `Footer` imports. New render order: `<SentimentHeatmap />` → `<SectorSentimentRow />` → `<NewsContent />` inside a `home-page` div constrained to `max-width: 1400px`.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None — all data flows are live:
- `SentimentHeatmap` reads `stocks` from `StockDataContext` (wired in 05-01)
- `SectorSentimentRow` fetches `/sector-sentiment` directly via `getSectorSentiment()`
- `NewsContent` was pre-existing and unchanged

---

## Self-Check: PASSED

| Item | Result |
|------|--------|
| SentimentHeatmap.js exists | FOUND |
| SentimentHeatmap.css exists | FOUND |
| SectorSentimentRow.js exists | FOUND |
| SectorSentimentRow.css exists | FOUND |
| HomePage.js rewritten | FOUND |
| HomePage.css created | FOUND |
| isAnimationActive={false} in SentimentHeatmap | FOUND (line 161) |
| All 5 palette stops present | FOUND (#dc2626, #f87171, #475569, #4ade80, #16a34a) |
| FEW_STOCK_TICKERS with EQIX/SPG/LIN | FOUND (line 31) |
| getSectorSentiment call in SectorSentimentRow | FOUND (line 24) |
| commit eb62fe6 (SentimentHeatmap) | FOUND |
| commit b800f61 (SectorSentimentRow + HomePage) | FOUND |
