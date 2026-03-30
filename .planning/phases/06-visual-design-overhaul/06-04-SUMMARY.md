---
phase: 06-visual-design-overhaul
plan: 04
subsystem: ui
tags: [react, css-grid, css-variables, news-layout, card-grid, responsive]

# Dependency graph
requires:
  - phase: 06-02
    provides: CSS variable tokens (--bg-surface, --bg-elevated, --border, --accent-blue, --text-primary, --text-secondary) established in theme.css
provides:
  - NewsData card grid layout: hero card (200px+1fr grid) + 3-column secondary row
  - getRelativeTime() helper for Unix timestamp → relative time display
  - getThumbnailUrl() helper with safe optional chaining for news thumbnails
  - Responsive mobile collapse at 768px breakpoint
affects: [06-visual-design-overhaul, human-verify checkpoint for Phase 6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline card markup pattern: components render their own layout markup directly rather than delegating to shared NewsItem child — avoids forcing a single DOM shape when hero and secondary cards have different structures"
    - "Image graceful degradation: onError hides broken images instead of showing placeholder URLs; CSS grid collapses gracefully when img is display:none"
    - "Stable list keys: key={news.link || index} — uses meaningful identifier when available, index as fallback"

key-files:
  created: []
  modified:
    - frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.css
    - frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.js

key-decisions:
  - "Inlined hero/secondary markup in NewsData.js directly rather than extending NewsItem — hero (thumbnail left + text right) and secondary (thumbnail top + text below) have fundamentally different DOM structures; forcing NewsItem to serve both would require complex prop drilling"
  - "Hero img hidden via display:none when no thumbnail rather than removed from DOM — avoids layout shift, CSS grid column collapses naturally"
  - "getThumbnailUrl uses resolutions?.[0]?.url — matches Yahoo Finance API shape confirmed via NewsItem.js inspection"

patterns-established:
  - "CSS variable-only styling: NewsData.css and NewsData.js contain zero hardcoded hex values — all colors via CSS custom properties"
  - "Card surface pattern: bg-surface + 1px border + 8px border-radius + hover border-color accent-blue transition"

requirements-completed: [VIS-08]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 6 Plan 04: NewsData Card Grid Rewrite Summary

**NewsData rewritten from flex-column layout to card grid: full-width hero (200px thumbnail left + text right) and 3-column secondary row, using CSS grid throughout with responsive mobile collapse and zero hardcoded hex values.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-30T11:48:37Z
- **Completed:** 2026-03-30T11:53:00Z
- **Tasks:** 2 (+ human-verify checkpoint pending)
- **Files modified:** 2

## Accomplishments

- Replaced entire NewsData.css (`.large-news`/`.small-news` flex layout) with card grid: `.news-hero-card` using `display:grid; grid-template-columns: 200px 1fr` and `.news-secondary-row` using `repeat(3, 1fr)`
- Rewrote NewsData.js to inline hero and secondary card markup directly — removed NewsItem import; added `getRelativeTime()` and `getThumbnailUrl()` helpers
- Mobile responsiveness: `@media (max-width: 768px)` collapses hero to single column and secondary row to single column

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite NewsData.css — card grid layout** - `d49c6a4` (feat)
2. **Task 2: Rewrite NewsData.js — inline hero and secondary card markup** - `430fd79` (feat)

## Files Created/Modified

- `frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.css` - Full replacement: card grid layout with hero + 3-column secondary, responsive mobile collapse, all CSS variables
- `frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.js` - Full replacement: inline card markup, getRelativeTime/getThumbnailUrl helpers, no NewsItem dependency, no hardcoded hex

## Decisions Made

- Inlined hero/secondary card markup in NewsData.js rather than extending NewsItem — the two card types have structurally different DOM layouts (left-thumbnail vs. top-thumbnail) making a shared component unnatural
- Used `news.publisher` as the source field name, confirmed by inspection of NewsItem.js which accesses the same news shape
- Hero image uses `display:none` when no thumbnail rather than conditionally omitting the `<img>` tag — reduces layout reflow and works cleanly with CSS grid column sizing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — the card markup is fully wired to the live API response from `getNewsData()`. Publisher, relative time, and thumbnail all derive from actual API data.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both Tasks 1 and 2 complete. Human verification checkpoint (Task 3) is pending — user must visually confirm:
- News hero card renders with thumbnail left + headline/source/time right
- 3 secondary cards appear in a horizontal row below the hero
- Mobile collapse works at 768px
- Dark/light theme toggle works across all Phase 6 components without FOUC

---
*Phase: 06-visual-design-overhaul*
*Completed: 2026-03-30*
