---
phase: 05-ui-overhaul-polish
plan: 04
subsystem: frontend/ui-wiring
tags: [react, mui, context, ticker-strip, skeleton, css-utilities]
dependency_graph:
  requires:
    - 05-01 (StockDataContext with isRefreshing, lastUpdated, refreshInterval, setRefreshInterval)
    - 05-03 (App.js with /stock/:ticker route already present)
  provides:
    - TopBar with LinearProgress refresh indicator, last-updated timestamp, settings gear dialog
    - Fixed-bottom ticker strip (StockChart + StockDetails) consuming stocks from context
    - Global CSS utilities: .section-label, .pct-badge, .pct-badge--up, .pct-badge--down, body padding-bottom
    - NewsData with Skeleton loading state and error+Retry
  affects:
    - All pages (StockChart persists via App.js sibling placement)
    - Homepage news section (skeleton improves perceived load time)
tech_stack:
  added: []
  patterns:
    - LinearProgress with position:fixed and zIndex:9999 for non-intrusive refresh indicator
    - MUI Dialog for settings — dark theme via PaperProps.sx, DialogActions with two distinct CTAs
    - CSS marquee loop via duplicated list (-50% translateX to loop seamlessly)
    - hover pause via animation-play-state:paused on .ticker-strip:hover .ticker-strip-track
    - Dynamic import() for news.json to get async loading/error pattern from static JSON
key_files:
  created: []
  modified:
    - frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.js
    - frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.css
    - frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.js
    - frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.css
    - frontend/stock_sentiment_analysis/src/components/StockDetails/StockDetails.js
    - frontend/stock_sentiment_analysis/src/components/StockDetails/StockDetails.css
    - frontend/stock_sentiment_analysis/src/App.js
    - frontend/stock_sentiment_analysis/src/App.css
    - frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.js
    - frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.css
decisions:
  - "TopBar uses useContext(StockDataContext) directly (not prop drilling) — settings state (settingsOpen, pendingInterval) kept local to TopBar since it has no external consumers"
  - "StockChart list duplicated in JSX (not CSS) — explicit duplication makes the seamless-loop logic visible and avoids relying on CSS content duplication hacks"
  - "NewsData uses dynamic import() for news.json — gives a genuine async loading/error boundary for static content; future replacement with API call requires only changing the import path"
  - "body padding-bottom placed in App.css (global reset file) not index.css — collocated with other App-level layout rules"
metrics:
  duration: "~5 min"
  completed: "2026-03-29"
  tasks: 3
  files: 10
---

# Phase 05 Plan 04: UI Wiring — TopBar Refresh, Ticker Strip, Global CSS, News Skeleton Summary

**One-liner:** Wired TopBar to StockDataContext for LinearProgress refresh indicator and settings dialog; converted StockChart to a position:fixed dark-themed ticker strip with pct-badge pills; added global CSS utility classes; retrofitted NewsData with MUI Skeleton loading and Retry error state.

---

## What Was Built

### Task 1 — TopBar.js + TopBar.css (commit 5e294a9)

Rewrote `TopBar.js` to consume `{ isRefreshing, lastUpdated, refreshInterval, setRefreshInterval }` from `StockDataContext`.

**LinearProgress:** Rendered as a Fragment sibling above the `.header` div. Uses `position: fixed; top: 0; left: 0; right: 0; height: 2px; zIndex: 9999` via MUI `sx` prop. Only rendered when `isRefreshing === true` — conditionally mounted so it disappears when polling completes.

**Timestamp:** `<span className="last-updated-text">` shows `'Updating…'` during refresh, `'Last updated H:MM AM/PM'` when idle (formatted via `toLocaleTimeString` with `hour12: true`). Returns empty string when `lastUpdated` is null (initial load).

**Settings gear:** `<IconButton aria-label="Refresh interval settings">` opens a dark-themed MUI Dialog. Dialog shows a `<Select>` with 5 min / 10 min / 30 min options bound to `pendingInterval` state. On open, `pendingInterval` is reset to `refreshInterval` so cancellation leaves the setting unchanged. `Save Settings` calls `setRefreshInterval(pendingInterval)`. `Keep Current Settings` calls `setSettingsOpen(false)` without applying changes.

**CSS additions:** `.topbar-right` (flex row, gap 8px) wraps timestamp, gear, and nav link. `.last-updated-text` applies `font-variant-numeric: tabular-nums` for stable width during time updates.

### Task 2 — StockChart, StockDetails, App.js, App.css (commit bec60d2)

**StockChart.js:** Replaced `const stockData = useContext(StockDataContext)` (treated as flat array) with `const { stocks } = useContext(StockDataContext)`. Returns null when stocks is empty/undefined. Renders two copies of the stock list in `.ticker-strip-track` — the duplicate enables the CSS `translateX(-50%)` loop to reset seamlessly.

**StockChart.css:** Full replacement — `position: fixed; bottom: 0; left: 0; width: 100%; height: 40px; z-index: 1000; background-color: #0f172a; border-top: 1px solid rgba(255,255,255,0.1)`. Ticker track animates via `tickerScroll` keyframe (80s linear infinite). Hover pauses animation via `animation-play-state: paused`.

**StockDetails.js:** Full replacement — shows `<Link to="/stock/{name}">` (ticker symbol), `$price.toFixed(2)` span, and `pct-badge pct-badge--up/--down` pill computed from `percent_change`. Uses `?? 0` guard for null values.

**StockDetails.css:** Full replacement — `.ticker-cell` (flex row, 40px height, border-right divider). `.ticker-symbol` and `.ticker-price` use JetBrains Mono with `font-variant-numeric: tabular-nums`.

**App.js:** Added `import StockChart from './components/StockChart/StockChart'` and `<StockChart />` after `</Routes>` inside `<Router>` — ensures the ticker strip persists across all route changes.

**App.css:** Appended `body { padding-bottom: 48px }` (prevents content being hidden behind fixed strip). Added `.section-label` (uppercase, `letter-spacing: 0.08em`, `0.75rem`, `#94a3b8`). Added `.pct-badge`, `.pct-badge--up`, `.pct-badge--down` global pill badge classes with `tabular-nums` and RGBA tinted backgrounds.

### Task 3 — NewsData.js + NewsData.css (commit f4493fa)

Rewrote `NewsData.js` with async loading/error pattern using `useState`/`useEffect` and dynamic `import()`.

**Loading state:** `loading` defaults to `true`. Renders `.news-section` with one large `<Skeleton variant="rectangular" height={240}>` (for the hero news item slot) and three small `<Skeleton height={80}>` (for the secondary items). Both use `bgcolor: 'rgba(255,255,255,0.08)'` and rounded corners to match the dark background.

**Error state:** If `import('../../news.json')` rejects, sets `error` message. Renders centered `.news-section.news-error` div with error text and an outlined MUI `<Button>` labeled `Retry` that re-calls `loadNews()`.

**Loaded state:** Shows `<h2 className="section-label">Latest News</h2>` heading, then the original `largeNewsItem` + `smallNewsItems.slice(1,4)` + `<TopCompanies />` layout.

**CSS addition:** `.news-error { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 200px; text-align: center; }`.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None — all logic is fully wired:
- TopBar reads live context state (no hardcoded refresh state)
- StockChart reads live `stocks` from context
- NewsData uses `import()` — identical async pattern that would be used for a real API call; no hardcoded mock data

---

## Self-Check: PASSED

| Item | Result |
|------|--------|
| TopBar.js isRefreshing present | FOUND (line 31, 53) |
| TopBar.js lastUpdated present | FOUND (line 31, 74) |
| TopBar.js LinearProgress present | FOUND (line 5, 54) |
| TopBar.js SettingsIcon present | FOUND (line 17, 82) |
| TopBar.js Save Settings button | FOUND |
| TopBar.js Keep Current Settings button | FOUND |
| TopBar.css .topbar-right present | FOUND |
| TopBar.css .last-updated-text present | FOUND |
| StockChart.css position:fixed present | FOUND (line 2) |
| StockChart.css bottom:0 present | FOUND (line 3) |
| StockChart.css z-index:1000 present | FOUND |
| StockChart.js stocks destructured | FOUND (line 8) |
| StockDetails.js pct-badge pill present | FOUND |
| StockDetails.js Link to /stock/:ticker | FOUND |
| App.js StockChart import present | FOUND (line 7) |
| App.js StockChart after Routes | FOUND (line 24) |
| App.css body padding-bottom:48px | FOUND (line 9) |
| App.css .section-label present | FOUND |
| App.css .pct-badge present | FOUND (line 24) |
| App.css .pct-badge--up present | FOUND (line 34) |
| App.css .pct-badge--down present | FOUND (line 39) |
| NewsData.js Skeleton present | FOUND (lines 34, 39) |
| NewsData.js loadNews/error/Retry | FOUND (lines 13, 47, 51) |
| NewsData.js section-label heading | FOUND (line 64) |
| commit 5e294a9 (TopBar) | FOUND |
| commit bec60d2 (StockChart/StockDetails/App) | FOUND |
| commit f4493fa (NewsData) | FOUND |
