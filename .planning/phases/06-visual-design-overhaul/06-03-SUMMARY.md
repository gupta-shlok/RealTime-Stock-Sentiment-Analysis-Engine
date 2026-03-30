---
phase: 06-visual-design-overhaul
plan: "03"
subsystem: frontend/components
tags: [css-variables, recharts, company-page, glassmorphism, design-system]
dependency_graph:
  requires: ["06-01"]
  provides: ["chartTheme-utility", "company-page-css-variables"]
  affects: ["frontend/stock_sentiment_analysis/src/components/CompanyPage"]
tech_stack:
  added: ["chartTheme.js utility"]
  patterns: ["CSS variable token usage", "Recharts SVG constant separation"]
key_files:
  created:
    - frontend/stock_sentiment_analysis/src/utils/chartTheme.js
  modified:
    - frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.css
    - frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js
decisions:
  - "CHART_THEME constants are intentionally hardcoded — SVG attributes bypass the CSS cascade and cannot use var() references"
  - "Recharts Cell fill values for sentiment bars left as-is — they are data-driven colors from getSentimentColor(), not theme constants"
  - ".glass-card border-radius changed from 16px to 8px to match global surface-card spec (D-29)"
  - "Duplicate .pct-badge and .section-label blocks removed; global App.css definitions are authoritative"
metrics:
  duration: "100 seconds"
  completed: "2026-03-30T11:44:49Z"
  tasks: 2
  files_changed: 3
requirements_satisfied: [VIS-06, VIS-07, VIS-09, VIS-10]
---

# Phase 6 Plan 03: CompanyPage CSS Variables and chartTheme Utility Summary

**One-liner:** CompanyPage refactored from glassmorphism and hardcoded hex values to CSS variable tokens, with Recharts SVG constants extracted to a dedicated chartTheme.js utility.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create chartTheme.js utility for Recharts color constants | ebdfa20 | `src/utils/chartTheme.js` (created) |
| 2 | Refactor CompanyPage.css and CompanyPage.js | a7cbf40 | `CompanyPage.css`, `CompanyPage.js` (modified) |

---

## What Was Built

### chartTheme.js (new file)

Created `frontend/stock_sentiment_analysis/src/utils/chartTheme.js` exporting a `CHART_THEME` object with 8 constants for all Recharts SVG props (`axisColor`, `gridColor`, `tooltipBg`, `tooltipBorder`, `priceStroke`, `priceFill`, `sentimentPos`, `sentimentNeg`). The file includes a comment block explaining why values are hardcoded — SVG attributes bypass the CSS cascade and cannot use `var()` references.

### CompanyPage.css

13 hardcoded values replaced with CSS variable references:
- `.price-change.up / .down`: `#10b981` / `#ef4444` → `var(--color-positive)` / `var(--color-negative)`
- `.glass-card`: `rgba(255,255,255,0.03)` background + `rgba(255,255,255,0.05)` border → `var(--bg-surface)` + `1px solid var(--border)`; `border-radius` normalized to `8px`
- `.chart-section h3`, `.metric-card span`, `.loading-spinner`, `.chart-error`, `.narrative-staleness`, `.narrative-pending-caption`, `.narrative-error`: all `#94a3b8` → `var(--text-secondary)`
- `.narrative-text`: `#cbd5e1` → `var(--text-primary)`
- Duplicate `.pct-badge` block (lines 206-224) removed entirely
- Duplicate `.section-label` block (lines 226-235) removed entirely

### CompanyPage.js

- Added `import { CHART_THEME } from '../../utils/chartTheme'`
- 2 `Skeleton` components: `bgcolor: 'rgba(255,255,255,0.08)'` → `backgroundColor: 'var(--bg-elevated)'`
- 2 `Button` error retry components: `color: '#94a3b8', borderColor: '#475569'` → `color: 'var(--text-secondary)', borderColor: 'var(--text-disabled)'`
- `CartesianGrid`: `stroke="rgba(255,255,255,0.07)"` → `stroke={CHART_THEME.gridColor}`
- `XAxis`: `stroke="#94a3b8"`, `tick={{ fill: '#94a3b8' }}` → CHART_THEME.axisColor
- Both `YAxis`: tick fill and stroke → CHART_THEME.axisColor / CHART_THEME.priceStroke
- `Tooltip` contentStyle: `backgroundColor: '#1e293b'` → `backgroundColor: CHART_THEME.tooltipBg`
- Sentiment bar `Cell` fill values NOT changed — data-driven colors remain inline

---

## Decisions Made

1. **chartTheme.js hardcoded constants**: SVG attributes on Recharts components (`stroke`, `fill`, `backgroundColor` in contentStyle) cannot consume CSS custom properties — the browser resolves them as attribute values outside the CSS cascade. Constants mirror the dark-theme token values and are explicitly documented as intentional.

2. **Recharts Cell fill unchanged**: The `Cell` fill values (`#4ade80`, `#f87171`) for sentiment bars are data-driven (positive/negative per entry) and controlled by `getSentimentColor()` logic. These are not theme styling — they are data encoding.

3. **.glass-card border-radius 16px → 8px**: Changed to match the global surface-card specification (D-29) which sets `border-radius: 8px`. Consistency across all surface cards takes precedence.

4. **Duplicate CSS blocks removed**: `.pct-badge` and `.section-label` were duplicated from App.css. The global definitions are authoritative; duplicates were removed to eliminate specificity conflicts (per research Pitfall 5).

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None — all changes wire to real CSS variables defined in theme.css (06-01); no placeholder values remain.

---

## Self-Check

### Files exist:

- `frontend/stock_sentiment_analysis/src/utils/chartTheme.js` — FOUND
- `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.css` — FOUND (modified)
- `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js` — FOUND (modified)

### Commits exist:

- `ebdfa20` — Task 1: chartTheme.js created
- `a7cbf40` — Task 2: CompanyPage CSS + JS refactored

## Self-Check: PASSED
