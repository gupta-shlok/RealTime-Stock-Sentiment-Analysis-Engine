---
status: testing
phase: 05-ui-overhaul-polish
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md]
started: 2026-03-30T06:59:38Z
updated: 2026-03-30T07:21:00Z
---

## Current Test

number: complete
name: All tests complete
awaiting: none

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch (docker compose up or equivalent). Backend boots without errors, any seed/migration completes, and a primary query (health check or homepage load) returns live data.
result: pass

### 2. Sentiment Heatmap on Homepage
expected: The homepage shows a Recharts Treemap at the top. Stocks are grouped into colored sector tiles. Colors range from red (negative sentiment) through grey/slate (neutral) to green (positive sentiment). Hovering a tile shows a tooltip with ticker, price, sentiment score, and percent change. Loading shows a pulsing skeleton.
result: pass

### 3. Sector Sentiment Row on Homepage
expected: Below the heatmap, a row of sector cards appears. Each card shows a sector name, an avg_score with sign prefix (e.g. +0.42 in green or -0.21 in red), and a stock count. Loading shows 5 skeleton rectangles. If the endpoint fails, an error message and "Retry" button appear.
result: pass

### 4. Homepage Layout Order
expected: The homepage renders in this vertical order: Sentiment Heatmap → Sector Sentiment Row → Latest News section. No old StockChart chart appears on the homepage. No Footer appears.
result: pass

### 5. TopBar Refresh Indicator
expected: When the app polls for new data in the background, a thin 2px blue LinearProgress bar appears pinned to the very top of the page (above the header). It disappears when the refresh completes. It does NOT appear during the initial page load (only on background polling).
result: pass

### 6. TopBar Last Updated Timestamp
expected: After the first data load, the TopBar shows a "Last updated H:MM AM/PM" timestamp (e.g. "Last updated 7:03 AM"). While refreshing it shows "Updating…". On the very first load before data arrives, nothing is shown for that slot.
result: pass

### 7. TopBar Settings Dialog
expected: Clicking the gear icon in the TopBar opens a dark-themed dialog. The dialog has a dropdown with 3 options: 5 min, 10 min, 30 min. Clicking "Save Settings" closes the dialog and changes the refresh interval. Clicking "Keep Current Settings" closes the dialog without changing anything.
result: pass

### 8. Fixed-Bottom Ticker Strip
expected: A dark horizontal bar is pinned to the bottom of every page. It shows a scrolling marquee of stock tickers with their price and a green/red pill showing percent change. Hovering the strip pauses the scroll. Page content does not get hidden behind the strip (padding-bottom applied).
result: pass

### 9. Ticker Strip Navigation to Company Page
expected: Clicking a ticker symbol in the bottom strip navigates to /stock/:ticker (e.g. /stock/AAPL). The Company Page loads with the correct stock's data.
result: pass

### 10. Company Page Dual-Axis Chart
expected: The Company Page shows a ComposedChart with price as an area on the left Y-axis and sentiment as color-coded bars on the right Y-axis (green for positive, red for negative). Both axes are visible and labeled. The chart covers the last 7 days.
result: pass

### 11. Company Page AI Narrative
expected: Below the chart, an "AI Narrative" section shows a loading skeleton (96px tall) initially. After a short wait it shows a generated text narrative for the stock. A "Generated X min ago" caption appears below the text.
result: skipped
reason: Qwen model intentionally disabled during Phase 5 testing (10-15 min CPU load). To be re-enabled after Phase 6.

### 12. Company Page pct-badge Pill
expected: The percent change for the stock is shown as a rounded pill badge — green-tinted background with green text for positive change, red-tinted background with red text for negative change.
result: pass

### 13. NewsData Skeleton Loading
expected: On homepage load, the Latest News section briefly shows a large skeleton placeholder (for the hero slot) and three smaller skeletons (for secondary items) before real news content appears. If news fails to load, an error message and "Retry" button appear.
result: pass
note: Skeletons replaced with CircularProgress spinner — skeleton bgcolor was invisible on light background. Error state with Retry confirmed present.

### 14. Refresh Interval Persists Across Reload
expected: Change the refresh interval to 5 min via the settings dialog. Reload the page. Open settings again — the dropdown still shows 5 min (not the default 10 min). The setting was persisted to localStorage.
result: pass

## Summary

total: 14
passed: 13
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

[none yet]
