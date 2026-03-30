# Phase 6: Visual Design Overhaul - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the app from a functional-but-dated layout into a cohesive dark/light-themeable financial dashboard. All components are built — this phase is purely visual: CSS variable system, dark/light theme, app branding rename, TopBar polish, news layout redesign, and consistent surface styling across all pages. No new features, no new endpoints.

</domain>

<decisions>
## Implementation Decisions

### App Branding
- **D-01:** The app is named **StockSentimentSense**. The TopBar displays this as a text logo (no image). The existing `download.png` logo and orange `h1` color are removed entirely.
- **D-02:** The text logo uses the app name in a clean sans-serif weight — styling at Claude's discretion (bold, accent color, or gradient — something that reads as a brand name, not generic body text).

### Theme System
- **D-03:** The app supports **dark** and **light** themes, toggled by the user. Dark is the default.
- **D-04:** The theme toggle lives **inside the Settings dialog** (alongside the refresh interval dropdown) as a toggle button — not in the TopBar directly.
- **D-05:** Theme is persisted to `localStorage` (key: `sentiment_theme`) so it survives page reloads.
- **D-06:** Implementation: CSS custom properties on `:root` with a `[data-theme="light"]` attribute override on `<html>`. The `data-theme` attribute is set by JavaScript on mount and on toggle. No MUI theme changes needed — MUI components that already have dark-specific inline `sx` props will be updated to read from CSS variables or conditionally from a React theme context.

### Color Palette (Dark theme — default)
- **D-07:** Page background: `#0f172a` (deep navy-black)
- **D-08:** Card / panel surface: `#1e293b` (elevated dark slate)
- **D-09:** Elevated surface (modals, dropdowns): `#334155`
- **D-10:** Primary text: `#f1f5f9`; Secondary/muted text: `#94a3b8`; Disabled: `#475569`
- **D-11:** Border / divider: `rgba(255,255,255,0.08)`
- **D-12:** Accent blue: `#3b82f6`; Positive green: `#4ade80`; Negative red: `#f87171`

### Color Palette (Light theme)
- **D-13:** Page background: `#f8fafc`
- **D-14:** Card / panel surface: `#ffffff`
- **D-15:** Elevated surface: `#f1f5f9`
- **D-16:** Primary text: `#0f172a`; Secondary/muted text: `#64748b`; Disabled: `#94a3b8`
- **D-17:** Border / divider: `rgba(0,0,0,0.08)`
- **D-18:** Accent blue, green, red remain the same across themes.

### CSS Variable System
- **D-19:** All colors are centralized into CSS custom properties defined in `App.css` (or a new `theme.css` imported globally). Variables follow a semantic naming convention: `--bg-page`, `--bg-surface`, `--bg-elevated`, `--text-primary`, `--text-secondary`, `--text-disabled`, `--border`, `--accent-blue`, `--color-positive`, `--color-negative`.
- **D-20:** All existing component CSS files are refactored to reference these variables instead of hardcoded hex values. Scattered `#1e293b`, `#94a3b8`, etc. across 15 CSS files are replaced with var references.
- **D-21:** MUI component `sx` props that hardcode colors (TopBar dialog, SectorSentimentRow scores, etc.) are updated to reference CSS variables via `var(--variable-name)` or a shared JS constants object — whichever is cleaner per component.

### TopBar Redesign
- **D-22:** TopBar background: `var(--bg-surface)` with a `1px solid var(--border)` bottom border. No more flat black.
- **D-23:** Left side: "StockSentimentSense" text logo. Right side: Last-updated text, gear/settings icon, "Custom Sentiment" nav link — same layout as Phase 5 but restyled to match the new surface.
- **D-24:** The `h1` orange color (`rgb(247,105,0)`) and `#logo` image reference in TopBar.css are removed.

### News Layout
- **D-25:** The news section is redesigned as a **card-based layout**: the hero item is a full-width card with a thumbnail image on the left and headline/source/time on the right. Below it, 3 secondary items render in a horizontal row of smaller cards (image + headline + source). Cards use `var(--bg-surface)`, a `1px solid var(--border)` border, and `8px` border-radius.
- **D-26:** On mobile (< 768px), the 3-column secondary row collapses to a single column.
- **D-27:** The loading state already uses `CircularProgress` (fixed in Phase 5 UAT) — this is kept as-is.

### Card Surfaces (Global)
- **D-28:** No glassmorphism. All card/panel surfaces use flat `var(--bg-surface)` with a subtle border — cleaner for a data-dense financial dashboard.
- **D-29:** Sector cards, heatmap container, company page sections, and news cards all use the same surface treatment: `background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px`.

### Skeleton Loaders
- **D-30:** Skeleton `bgcolor` is updated to use `var(--bg-elevated)` so skeletons are visible on both dark and light backgrounds. The hardcoded `rgba(255,255,255,0.08)` value (invisible on light backgrounds, identified in Phase 5 UAT) is replaced everywhere.

### Claude's Discretion
- Exact text logo styling (font weight, size, possible gradient or accent color)
- Whether to use a single `theme.css` file or keep variables in `App.css`
- Exact padding/spacing adjustments to news card layout
- Hover states on cards and interactive elements
- Transition duration for theme switch (suggest 200ms on background/color properties)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing CSS files to refactor
- `frontend/stock_sentiment_analysis/src/App.css` — Global styles, pill badge, section-label, body padding
- `frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.css` — Current TopBar with hardcoded black bg and orange h1
- `frontend/stock_sentiment_analysis/src/components/HomePage/HomePage.css`
- `frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.css`
- `frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.css`
- `frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.css` — Current news layout (50vw hero + flex row)
- `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.css`
- `frontend/stock_sentiment_analysis/src/components/StockChart/StockChart.css`

### Existing JS components with hardcoded colors (sx props to update)
- `frontend/stock_sentiment_analysis/src/components/TopBar/TopBar.js` — Settings dialog hardcodes `#1e293b`, `#334155`, `#f1f5f9`, `#3b82f6`
- `frontend/stock_sentiment_analysis/src/components/SectorSentimentRow/SectorSentimentRow.js`
- `frontend/stock_sentiment_analysis/src/components/SentimentHeatmap/SentimentHeatmap.js`
- `frontend/stock_sentiment_analysis/src/components/NewsData/NewsData.js`
- `frontend/stock_sentiment_analysis/src/components/CompanyPage/CompanyPage.js`

### Phase 5 context (design decisions locked upstream)
- `.planning/phases/05-ui-overhaul-polish/05-CONTEXT.md` — D-09 (heatmap palette), D-21 (skeleton dark bgcolor — now superseded by D-30), D-23 (pill badge colors), D-24 (section label typography)

### Prior phase palette reference
- Color tokens established in Phase 5 are the source of truth: `#0f172a`, `#1e293b`, `#334155`, `#94a3b8`, `#f1f5f9`, `#4ade80`, `#f87171`, `#3b82f6`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.pct-badge`, `.pct-badge--up`, `.pct-badge--down` in `App.css` — already use correct colors, just need var() references
- `.section-label` in `App.css` — hardcodes `#94a3b8`, replace with `var(--text-secondary)`
- `StockDataContext` theme state — theme preference can be added here alongside `refreshInterval`, or managed in a separate lightweight context

### Established Patterns
- MUI components use inline `sx` props for dark-specific styling — these must be updated per-component to respond to theme (either via CSS vars or a React `theme` prop passed down)
- `localStorage` is already used for `sentiment_refresh_interval` — same pattern applies to `sentiment_theme`
- All CSS files are co-located with their component — refactor stays in-place, no file moves needed

### Integration Points
- `index.js` or `App.js` — set `data-theme` attribute on `document.documentElement` on initial load (read from localStorage) and on toggle
- `TopBar.js` — add theme toggle UI to the Settings dialog; call the toggle handler from context
- `NewsData.js` + `NewsData.css` — full layout rewrite for card-based design
- `TopBar.js` — remove `<img id="logo">` and `h1` orange styling; replace with text logo span

</code_context>

<specifics>
## Specific Ideas

- App name: **StockSentimentSense** — text only in TopBar, no image
- Theme toggle: toggle button (sun/moon or "Light / Dark" label) inside the existing Settings MUI Dialog, below the refresh interval control
- localStorage keys: `sentiment_theme` (values: `"dark"` | `"light"`), default `"dark"`
- `data-theme` attribute set on `<html>` element (not body) — standard pattern, avoids FOUC when set before first paint
- News cards: left-aligned thumbnail (if image available), fallback to a colored placeholder if no image. Source name + relative time ("2h ago") below headline in muted text.

</specifics>

<deferred>
## Deferred Ideas

- Glassmorphism (backdrop-filter blur) — explicitly decided against for this phase; could revisit in a future polish pass
- MUI theme provider integration — keeping CSS variables only for now; MUI ThemeProvider would unlock more systematic MUI component theming but adds scope
- Custom font loading (beyond JetBrains Mono already in use) — out of scope

</deferred>

---

*Phase: 06-visual-design-overhaul*
*Context gathered: 2026-03-30*
