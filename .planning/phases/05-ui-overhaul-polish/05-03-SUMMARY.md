---
phase: 05-ui-overhaul-polish
plan: 03
subsystem: frontend/company-page
tags: [react, recharts, mui, dual-axis-chart, narrative-polling, responsive]
dependency_graph:
  requires:
    - 05-01 (StockDataContext with stocks shape, getSentimentTrends, getStockNarrative)
  provides:
    - /stock/:ticker route in App.js rendering CompanyPage
    - CompanyPage dual-axis ComposedChart (price left Y, sentiment right Y)
    - AI narrative section with Skeleton loader, staleness caption, 10s polling
    - pct-badge pill for percent change display
    - Responsive 2-column metrics grid at 768px breakpoint
  affects:
    - App.js (new route added)
    - CompanyPage.js (full retrofit)
    - CompanyPage.css (new classes appended)
tech_stack:
  added: []
  patterns:
    - useMemo to merge price history and sentiment trend data by date key (chartDataWithSentiment)
    - useRef (narrativePollRef) for interval handle + narrativePollCountRef for 30-poll timeout guard
    - clearInterval in useEffect return cleanup to prevent memory leaks on ticker change / unmount
    - isAnimationActive={false} on Area and Bar to keep chart mounted during background data refresh (no blank flash)
    - Cell coloring inside Bar using map over chartDataWithSentiment — positive >= 0 gets #4ade80, negative #f87171
key_files:
  created: []
  modified:
    - frontend/stock_sentiment_analysis/src/App.js
    - frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js
    - frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.css
decisions:
  - "chartDataWithSentiment uses chartData.slice(-7) aligned to the 7d sentiment-trends window — consistent data range on both axes"
  - "narrativePollRef.current holds the setInterval ID; return cleanup in useEffect clears it on both unmount and ticker change (prevents stale poll targeting old ticker)"
  - "isAnimationActive=false on both Area and Bar — prevents Recharts re-mount animation flash when StockDataContext background refresh updates stocks prop"
  - "Narrative Skeleton shown for full height 96px to prevent layout shift when real text loads"
metrics:
  duration: "~2 min"
  completed: "2026-03-29"
  tasks: 2
  files: 3
---

# Phase 05 Plan 03: Company Page — Dual-Axis Chart & AI Narrative Summary

**One-liner:** Retrofitted CompanyPage with a Recharts ComposedChart dual-axis overlay (price Area left / sentiment Bar right with per-cell green-red coloring), AI narrative section with 10s polling and staleness caption, pct-badge pill, and responsive 768px breakpoint.

---

## What Was Built

### Task 1 — Add /stock/:ticker route to App.js (commit 58f3244)

Added `import CompanyPage from './components/CompanyPage/CompanyPage'` and `<Route path="/stock/:ticker" element={<CompanyPage />} />` inside the existing Routes block. The two existing routes (/ and /custom-sentiment) are preserved exactly.

### Task 2 — Retrofit CompanyPage with dual-axis chart and AI narrative (commit 7ab698d)

**Context adapter:** Replaced `const stockData = useContext(StockDataContext); stockData.find(...)` with `const { stocks } = useContext(StockDataContext); stocks.find(...)` to align with the shape introduced in Plan 05-01. This was a known planned adapter (documented in 05-01-SUMMARY Known Adapter Requirements).

**Dual-axis ComposedChart:**
- `chartDataWithSentiment` useMemo merges `stock.history` (last 7 entries, keyed on `d.Date`) with `sentimentTrends` (keyed on `t.date`) into combined data points with a `sentiment` field
- Left Y-axis (`yAxisId="left"`) hosts `<Area>` for price — stroke `#3b82f6`, gradient fill, `isAnimationActive={false}`
- Right Y-axis (`yAxisId="right"`) hosts `<Bar>` for sentiment — `domain={[-1, 1]}`, `isAnimationActive={false}`, per-`<Cell>` coloring: `#4ade80` for `sentiment >= 0`, `#f87171` for negative
- Chart stays mounted on background data refresh — only the `data` prop changes, no unmount flash

**Sentiment trends useEffect:** Fetches `getSentimentTrends(ticker, '7d')` on ticker change. Exposes `trendsLoading` / `trendsError` states. Error state renders a retry Button.

**AI narrative polling useEffect:** Calls `getStockNarrative(ticker)` immediately then every 10s via `setInterval`. Stops polling when `status === 'complete'` or after 30 polls (5-minute timeout). `narrativePollRef.current` holds the interval ID; `return () => clearInterval(narrativePollRef.current)` cleans up on ticker change and unmount. Error state renders a retry Button that re-starts the poll cycle.

**Narrative section JSX:** Shows MUI `Skeleton` (height 96px) while loading, error div with retry on failure, and `narrative.narrative` text + `Generated X min ago` caption (computed as `Math.floor((Date.now() - new Date(narrative.generated_at)) / 60000)`) when complete.

**pct-badge pill:** Replaced raw `.price-change.up/.down` span with `.pct-badge .pct-badge--up/.pct-badge--down` — rounded pill with background tint, tabular-nums monospace font.

**CSS additions (appended, no existing rules removed):**
- `.chart-error` — centered error state with 200px height
- `.narrative-section`, `.narrative-text`, `.narrative-staleness`, `.narrative-pending-caption`, `.narrative-error` — AI narrative layout
- `.pct-badge`, `.pct-badge--up`, `.pct-badge--down` — pill badge system
- `.section-label` — uppercase small-caps section header typography
- `@media (max-width: 768px) .metrics-grid` — collapses from auto-fit to `repeat(2, 1fr)`

---

## Deviations from Plan

### Auto-fixed Issues

None — all changes were prescribed in the plan. The context adapter (`stocks` destructure) was a planned action documented in 05-01-SUMMARY.

---

## Known Stubs

None — all data paths are wired:
- `getSentimentTrends` is a real Phase 4 endpoint function in `api.js`
- `getStockNarrative` is a real Phase 4 endpoint function in `api.js`
- `StockDataContext.stocks` provides the full stock array including `history`
- No hardcoded data, no TODO placeholders

---

## Self-Check

| Item | Result |
|------|--------|
| App.js Route path="/stock/:ticker" present | FOUND (line 21) |
| CompanyPage imports ComposedChart, Area, Bar, Cell | FOUND (line 6) |
| CompanyPage imports getSentimentTrends, getStockNarrative | FOUND (line 4) |
| chartDataWithSentiment useMemo present | FOUND (line 32) |
| yAxisId="left" on Area | FOUND (line 162) |
| yAxisId="right" on Bar, domain=[-1,1] | FOUND (lines 165-166) |
| narrativePollRef + clearInterval cleanup | FOUND (line 25, 105) |
| pct-badge in JSX | FOUND (line 125) |
| CompanyPage.css .pct-badge--up / .pct-badge--down | FOUND (lines 216, 221) |
| CompanyPage.css .narrative-section | FOUND |
| CompanyPage.css @media (max-width: 768px) .metrics-grid | FOUND |
| commit 58f3244 (App.js route) | FOUND |
| commit 7ab698d (CompanyPage retrofit) | FOUND |

## Self-Check: PASSED
