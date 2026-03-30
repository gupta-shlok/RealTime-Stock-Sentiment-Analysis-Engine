---
phase: 06-visual-design-overhaul
plan: 02
subsystem: frontend
tags: [css-variables, topbar, theming, surface-card, glassmorphism-removal]
dependency_graph:
  requires: [06-01]
  provides: [VIS-04, VIS-05, VIS-06, VIS-07, VIS-09, VIS-10]
  affects: [TopBar, SentimentHeatmap, SectorSentimentRow, StockChart, App.css]
tech_stack:
  added: []
  patterns:
    - CSS variable consumption in MUI sx props
    - surface-card utility class replacing glass-card globally
    - SVG fill via style prop for CSS variable support in Recharts
    - MenuProps PaperProps for theming MUI Select dropdown popover
key_files:
  created: []
  modified:
    - frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.js
    - frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.css
    - frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.css
    - frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.js
    - frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.css
    - frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.js
    - frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.css
    - frontend/stock_sentiment_analysis/src/App.css
decisions:
  - "SVG fill attributes converted to style prop to enable CSS variable resolution in Recharts sector labels"
  - "SectorSentimentRow Skeleton uses backgroundColor (not bgcolor) to bypass MUI palette system and honor CSS variables"
  - "MenuProps PaperProps added to Select component so dropdown popover background is themed (not unthemed white in light mode)"
metrics:
  duration: "~5 min"
  completed: "2026-03-30"
  tasks: 2
  files: 8
---

# Phase 6 Plan 02: TopBar Restyle and CSS Variable Refactor Summary

TopBar rebranded to "StockSentimentSense" text logo with CSS variable styling, theme toggle added to Settings dialog, and .glass-card replaced globally with .surface-card across SentimentHeatmap, SectorSentimentRow, and StockChart.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Restyle TopBar — text logo, CSS variable sx props, theme toggle | 0bfc6c1 | TopBar.js, TopBar.css |
| 2 | CSS variable refactor — SentimentHeatmap, SectorSentimentRow, StockChart; .surface-card in App.css | 9e2b421 | SentimentHeatmap.css, SentimentHeatmap.js, SectorSentimentRow.css, SectorSentimentRow.js, StockChart.css, App.css |

## What Was Built

**Task 1 — TopBar restyle:**
- Replaced `<a href="/"><img src="download.png" alt="Logo" id="logo" /></a>` with `<span className="topbar-brand">StockSentimentSense</span>`
- Added `LightModeIcon` and `DarkModeIcon` MUI icon imports
- Added `Box` and `Typography` to MUI material imports
- Destructured `theme` and `setTheme` from `StockDataContext`
- All hardcoded hex values in TopBar.js sx props replaced with CSS variables (`var(--accent-blue)`, `var(--text-secondary)`, `var(--bg-surface)`, `var(--text-primary)`, `var(--border)`, `var(--bg-elevated)`, `var(--text-disabled)`)
- Added `MenuProps={{ PaperProps: { sx: { backgroundColor: 'var(--bg-surface)' } } }}` to Select so dropdown popover is themed
- Added theme toggle block in DialogContent: sun icon (light mode) / moon icon (dark mode) wired to `setTheme`
- TopBar.css: `.header` background changed to `var(--bg-surface)` with `border-bottom: 1px solid var(--border)`; removed `h1 { color: rgb(247,105,0) }`, `#logo`, `.logo-container` rules; added `.topbar-brand` class

**Task 2 — CSS variable refactor and surface-card:**
- App.css: appended `.surface-card` utility class with `background: var(--bg-surface)`, `border: 1px solid var(--border)`, `border-radius: 8px`, `padding: 16px`
- SentimentHeatmap.css: `.heatmap-tooltip` uses `var(--bg-surface)` and `var(--border)`; `.tooltip-price`, `.tooltip-sentiment`, `.heatmap-error`, `.heatmap-empty` use `var(--text-secondary)`
- SentimentHeatmap.js: skeleton div uses `var(--bg-elevated)` instead of `rgba(255,255,255,0.08)`; outer div changed from `glass-card` to `surface-card`; sector label SVG fill moved from `fill` attribute to `style` prop to allow CSS variable resolution
- SectorSentimentRow.css: `.sector-count` and `.sector-row-error` use `var(--text-secondary)`
- SectorSentimentRow.js: Skeleton uses `backgroundColor: 'var(--bg-elevated)'` (not `bgcolor` shorthand); error Button uses `var(--text-secondary)` and `var(--text-disabled)`; sector card divs use `surface-card` class
- StockChart.css: `.ticker-strip` uses `var(--bg-page)` and `var(--border)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SVG fill attribute cannot resolve CSS variables**
- **Found during:** Task 2
- **Issue:** `SentimentHeatmap.js` line 68 used `fill={labelColor}` as an SVG presentation attribute with `#94a3b8` (and `#64748b` for "OTHER" sector). SVG presentation attributes bypass CSS variable resolution — only `style` prop properties can resolve CSS custom properties.
- **Fix:** Moved fill into the `style` prop: `style={{ textTransform: 'uppercase', pointerEvents: 'none', fill: isOther ? 'var(--text-disabled)' : 'var(--text-secondary)' }}`. Removed the `labelColor` variable entirely.
- **Files modified:** `SentimentHeatmap.js`
- **Commit:** 9e2b421

## Known Stubs

None. All changes are wiring real CSS variables from `theme.css` (created in Plan 01). No placeholder values remain.

## Self-Check: PASSED

Files verified:
- `frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.js` — exists, contains `StockSentimentSense`, `setTheme`, `LightModeIcon`
- `frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.css` — exists, contains `var(--bg-surface)`, `.topbar-brand`
- `frontend/stock_sentiment_analysis/src/App.css` — exists, contains `.surface-card`
- `frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.js` — exists, contains `surface-card`, `var(--bg-elevated)`
- `frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.js` — exists, contains `surface-card`, `backgroundColor: 'var(--bg-elevated)'`
- `frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.css` — exists, contains `var(--bg-page)`, `var(--border)`

Commits verified:
- `0bfc6c1` — Task 1 TopBar restyle
- `9e2b421` — Task 2 CSS variable refactor
