# Phase 6: Visual Design Overhaul - Research

**Researched:** 2026-03-30
**Domain:** CSS custom properties, React theme context, MUI sx-prop theming, CSS Grid card layouts, FOUC prevention
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** App is named **StockSentimentSense**. TopBar displays as text logo (no image). `download.png` logo and orange `h1` color removed entirely.
- **D-02:** Text logo uses clean sans-serif weight — styling at Claude's discretion (bold, accent color, or gradient).
- **D-03:** App supports **dark** and **light** themes, toggled by the user. Dark is the default.
- **D-04:** Theme toggle lives **inside the Settings dialog** (alongside the refresh interval dropdown) as a toggle button — not in the TopBar directly.
- **D-05:** Theme is persisted to `localStorage` (key: `sentiment_theme`) so it survives page reloads.
- **D-06:** Implementation: CSS custom properties on `:root` with a `[data-theme="light"]` attribute override on `<html>`. The `data-theme` attribute is set by JavaScript on mount and on toggle. No MUI ThemeProvider changes.
- **D-07–D-18:** Color palettes for dark and light themes (see CONTEXT.md for full hex values).
- **D-19:** All colors centralized into CSS custom properties in `App.css` (or a new `theme.css` imported globally). Semantic variable names: `--bg-page`, `--bg-surface`, `--bg-elevated`, `--text-primary`, `--text-secondary`, `--text-disabled`, `--border`, `--accent-blue`, `--color-positive`, `--color-negative`.
- **D-20:** All existing component CSS files refactored to reference these variables instead of hardcoded hex values.
- **D-21:** MUI component `sx` props updated to reference CSS variables via `var(--variable-name)` or a shared JS constants object.
- **D-22:** TopBar background: `var(--bg-surface)` with `1px solid var(--border)` bottom border.
- **D-23:** Left side: "StockSentimentSense" text logo. Right side: Last-updated, gear icon, Custom Sentiment link.
- **D-24:** Orange `h1` color and `#logo` image reference in TopBar.css removed.
- **D-25:** News section redesigned as card-based layout: hero = full-width card (thumbnail left + headline/source/time right); below = 3 secondary cards in horizontal row. Cards use `var(--bg-surface)`, `1px solid var(--border)`, `8px` border-radius.
- **D-26:** On mobile (< 768px), 3-column secondary row collapses to single column.
- **D-27:** Loading state uses existing `CircularProgress` — kept as-is.
- **D-28:** No glassmorphism. Flat `var(--bg-surface)` with subtle border for all cards/panels.
- **D-29:** Sector cards, heatmap container, company page sections, news cards all use: `background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px`.
- **D-30:** Skeleton `bgcolor` updated to `var(--bg-elevated)` — replacing hardcoded `rgba(255,255,255,0.08)`.

### Claude's Discretion

- Exact text logo styling (font weight, size, possible gradient or accent color)
- Whether to use a single `theme.css` file or keep variables in `App.css`
- Exact padding/spacing adjustments to news card layout
- Hover states on cards and interactive elements
- Transition duration for theme switch (suggest 200ms on background/color properties)

### Deferred Ideas (OUT OF SCOPE)

- Glassmorphism (backdrop-filter blur) — explicitly decided against for this phase
- MUI ThemeProvider integration — keeping CSS variables only
- Custom font loading (beyond JetBrains Mono already in use)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

Phase 6 introduces new visual design requirements (VIS-XX) not yet enumerated in REQUIREMENTS.md. Based on the locked decisions in CONTEXT.md, the requirements map as follows:

| ID | Description | Research Support |
|----|-------------|------------------|
| VIS-01 | CSS custom property token system established in a single file (`theme.css` or `App.css`) covering all 10 semantic variables for dark and light modes | CSS cascade research; single-file recommendation |
| VIS-02 | `data-theme` attribute set on `<html>` before first React paint, read from `localStorage` — no FOUC on reload | FOUC prevention pattern; inline script in `index.html` |
| VIS-03 | Theme toggle button in Settings dialog; persists to `localStorage` key `sentiment_theme`; default `"dark"` | React context extension pattern; localStorage pattern already present |
| VIS-04 | App renamed to "StockSentimentSense" — text logo in TopBar, orange `h1` and `download.png` removed | Direct code audit findings |
| VIS-05 | TopBar restyled: `var(--bg-surface)` background, `1px solid var(--border)` bottom border | Code audit; TopBar.css hardcoded values identified |
| VIS-06 | All 8 CSS files refactored to replace hardcoded hex values with CSS variable references | Full audit of hardcoded values completed below |
| VIS-07 | All MUI `sx` props with hardcoded colors updated to `var(--variable-name)` | MUI CSS variable compatibility confirmed |
| VIS-08 | News section redesigned as card layout (hero + 3-column secondary grid) with thumbnail, headline, source, relative time | CSS Grid pattern; NewsItem.js rewrite scope confirmed |
| VIS-09 | Skeleton loaders updated from `rgba(255,255,255,0.08)` to `var(--bg-elevated)` | MUI Skeleton bgcolor research; limitation documented |
| VIS-10 | Consistent surface treatment applied globally: `var(--bg-surface)` + `1px solid var(--border)` + `8px border-radius` | `.glass-card` class replacement strategy |

</phase_requirements>

---

## Summary

Phase 6 is a pure CSS/JS visual refactor with no backend changes and no new React component logic. Every component already exists; the work is (1) establishing a CSS variable token system, (2) wiring a theme context so the `data-theme` attribute on `<html>` controls which palette is active, (3) replacing every hardcoded hex color in CSS files and MUI `sx` props with variable references, and (4) rewriting the news layout as a proper card grid.

The architecture is clean. React is already reading `refreshInterval` from `localStorage` in `StockDataContext` — the same pattern applies to `sentiment_theme`. The `data-theme` attribute approach is the industry-standard way to switch CSS custom property themes without MUI ThemeProvider involvement. The only non-obvious pitfall is FOUC: because React renders client-side, the HTML document will flash with the default `:root` styles for one frame before the component tree reads localStorage and sets `data-theme`. This is solved by inserting a tiny blocking inline `<script>` in `public/index.html` that runs synchronously before the `<body>` is painted.

The news card redesign is the most structural change. `NewsData.js` currently renders a `<div className="large-news">` (50vw wide) and a `<div className="small-news">` (flex column). The rewrite changes this to a CSS Grid layout where the hero card uses a horizontal image+text layout and the secondary row uses `grid-template-columns: repeat(3, 1fr)`. `NewsItem.js` needs to be extended to accept a `variant` prop (`"hero"` | `"secondary"`) that controls the internal layout.

**Primary recommendation:** Establish `theme.css` as a standalone file imported at the top of `App.css`. Keep `App.css` for global reset and utility classes. This separation makes the token layer independently reviewable and avoids a monolithic `App.css`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| CSS Custom Properties | Native (no package) | Theme token system | Zero runtime cost; cascade-based; no JS dependency |
| React Context API | Included in React 18 | Theme state + toggle handler | Already used in project (StockDataContext pattern) |
| MUI v5 (`@mui/material`) | 5.x (already installed) | Dialog, Skeleton, Button — already in use | No new installs; sx props accept `var()` strings natively |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `localStorage` (Web API) | Native | Persist theme preference | Same pattern as `sentiment_refresh_interval` already in place |
| CSS Grid | Native | News card 3-column layout | Better than Flexbox for 2D card grids with responsive collapse |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS custom properties | MUI ThemeProvider | MUI ThemeProvider is more complete for MUI-heavy apps but requires replacing all `sx` hex props with `theme.palette.*` references — large scope, deferred per D-06 |
| Inline `<script>` in index.html for FOUC | `useLayoutEffect` in App.js | `useLayoutEffect` runs after React commit, still causes one-frame flash for SSR-style pages; inline script is synchronous and blocks paint before any HTML renders |
| Separate `theme.css` | Variables at top of `App.css` | Both work; `theme.css` is cleaner for reviewability — Claude's discretion per CONTEXT.md |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
src/
├── theme.css                          # NEW — CSS variable token file
├── App.css                            # MODIFIED — import theme.css, keep reset/utilities
├── context/
│   └── StockDataContext.js            # MODIFIED — add theme state + setTheme
├── components/
│   ├── TopBar/
│   │   ├── TopBar.js                  # MODIFIED — text logo, remove img, add theme toggle to dialog
│   │   └── TopBar.css                 # MODIFIED — remove hardcoded black bg and orange h1
│   ├── NewsData/
│   │   ├── NewsData.js                # MODIFIED — hero+3col grid layout
│   │   └── NewsData.css               # MODIFIED — card grid CSS
│   └── NewsItem/
│       └── NewsItem.js                # MODIFIED — accept variant prop, hero vs secondary layout
└── [all other component CSS files]    # MODIFIED — replace hardcoded hex with var()
```

### Pattern 1: CSS Variable Token File (`theme.css`)

**What:** A single CSS file defining all semantic color tokens as custom properties. The `:root` block holds dark-mode defaults (D-03 makes dark the default). A `[data-theme="light"]` block on `html` overrides the same variable names with light values.

**When to use:** Always — this is the source of truth for the entire color system.

**Example:**
```css
/* theme.css */
:root {
    --bg-page:        #0f172a;
    --bg-surface:     #1e293b;
    --bg-elevated:    #334155;
    --text-primary:   #f1f5f9;
    --text-secondary: #94a3b8;
    --text-disabled:  #475569;
    --border:         rgba(255, 255, 255, 0.08);
    --accent-blue:    #3b82f6;
    --color-positive: #4ade80;
    --color-negative: #f87171;
}

[data-theme="light"] {
    --bg-page:        #f8fafc;
    --bg-surface:     #ffffff;
    --bg-elevated:    #f1f5f9;
    --text-primary:   #0f172a;
    --text-secondary: #64748b;
    --text-disabled:  #94a3b8;
    --border:         rgba(0, 0, 0, 0.08);
    --accent-blue:    #3b82f6;
    --color-positive: #4ade80;
    --color-negative: #f87171;
}
```

Then in `App.css`, add at the top:
```css
@import './theme.css';
```

### Pattern 2: FOUC Prevention — Blocking Inline Script

**What:** A synchronous `<script>` tag in `public/index.html`, placed before `</head>` (or before `<div id="root">`). It reads `localStorage.getItem('sentiment_theme')` synchronously and sets `document.documentElement.setAttribute('data-theme', value)`. Because it's inline and blocking, it runs before the browser renders any HTML — no flash.

**Why this works:** The browser parses HTML top-to-bottom. An inline `<script>` in `<head>` blocks rendering until the script executes. By the time `<body>` is painted, `data-theme` is already set and CSS custom properties resolve to the correct values.

**Example:**
```html
<!-- public/index.html — inside <head>, after <meta> tags -->
<script>
  (function() {
    var theme = localStorage.getItem('sentiment_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  })();
</script>
```

**Critical detail:** This script must use `var` (not `const`/`let`) and an IIFE to be safe in older IE; but since this is a modern React app, `const` would work too. Using `var` + IIFE is the standard convention seen across all major theme-switching libraries (next-themes, etc.).

### Pattern 3: Theme Context — Extend StockDataContext

**What:** Add `theme` and `setTheme` to `StockDataContext`. The `setTheme` handler reads the new value, writes it to `localStorage`, AND calls `document.documentElement.setAttribute('data-theme', newTheme)` directly.

**Why StockDataContext (not a separate ThemeContext):** The project already has one context. Adding two fields (`theme`, `setTheme`) costs near zero complexity. A separate `ThemeContext` is warranted when theme state needs to be consumed by dozens of components independently — that is not the case here. The toggle is only in one place (Settings dialog in TopBar).

**Example:**
```javascript
// In StockDataContext.js — add to existing state
const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('sentiment_theme') || 'dark';
});

const setTheme = useCallback((newTheme) => {
    localStorage.setItem('sentiment_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    setThemeState(newTheme);
}, []);

// On mount, sync the attribute (redundant with inline script, but defensive)
useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

Add `theme` and `setTheme` to the Provider's `value` object and the default context shape.

### Pattern 4: MUI `sx` Props with CSS Variables

**What:** MUI v5's `sx` prop accepts any valid CSS string value, including `var()` references. `backgroundColor: 'var(--bg-surface)'` works correctly.

**Caveats verified:**
- MUI resolves `sx` prop values through its styling engine. String values that are not in MUI's theme shorthand are passed through as-is to the underlying CSS. `var(--bg-surface)` is a valid CSS string, not an MUI theme token, so it passes through correctly.
- MUI's `Skeleton` component accepts `bgcolor` as a shorthand for `backgroundColor` in `sx`. However, `bgcolor: 'var(--bg-elevated)'` will NOT work because MUI's `bgcolor` shorthand maps through the MUI color palette system (e.g., `bgcolor: 'grey.800'`), not raw CSS. Use `sx={{ backgroundColor: 'var(--bg-elevated)' }}` instead.
- For `MenuItem` popover backgrounds: MUI renders `MenuItem` inside a `Popper`/`Paper` which has its own `background-color`. Setting `sx={{ backgroundColor: 'var(--bg-elevated)' }}` on `MenuItem` works, but the `Paper` wrapper also needs `PaperProps={{ sx: { backgroundColor: 'var(--bg-surface)' } }}` on the `Select` or `Menu` component.

**Example (from TopBar.js Dialog):**
```javascript
// Before (hardcoded):
PaperProps={{ sx: { backgroundColor: '#1e293b', color: '#f1f5f9' } }}

// After (CSS variable):
PaperProps={{ sx: { backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' } }}
```

### Pattern 5: News Card Layout — CSS Grid

**What:** Replace the current `display: flex` side-by-side layout with a two-row CSS Grid. Row 1: hero card spanning full width. Row 2: 3-column grid of secondary cards.

**Example:**
```css
/* NewsData.css — new layout */
.news-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.news-hero-card {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    text-decoration: none;
    color: inherit;
}

.news-hero-card img {
    width: 200px;
    height: 130px;
    object-fit: cover;
    border-radius: 6px;
    background: var(--bg-elevated); /* fallback if no image */
}

.news-secondary-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

.news-secondary-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    text-decoration: none;
    color: inherit;
}

.news-secondary-card img {
    width: 100%;
    height: 110px;
    object-fit: cover;
    border-radius: 6px;
    background: var(--bg-elevated);
}

.news-card-headline {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.4;
}

.news-card-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
}

/* Mobile: collapse secondary row */
@media (max-width: 768px) {
    .news-hero-card {
        grid-template-columns: 1fr; /* stack image above text */
    }
    .news-secondary-row {
        grid-template-columns: 1fr;
    }
}
```

**NewsItem.js extension:** The existing `NewsItem` renders a flat `<div class="news-item">` with no variant awareness. For the card layout, `NewsData.js` should inline the card markup directly rather than extending `NewsItem`, since the hero and secondary cards have different DOM structures. `NewsItem.js` can be kept for the `CompanyPage` news grid (which has its own layout).

### Anti-Patterns to Avoid

- **Applying `data-theme` to `<body>` instead of `<html>`:** The `<html>` element is the topmost ancestor of all CSS, including browser scrollbar styles and `<head>` meta. Applying the attribute to `<html>` ensures full cascade coverage. Body-level application misses `<html>` background.
- **Reading localStorage in a `useEffect` for FOUC prevention:** `useEffect` fires after the first render commit — too late. The inline script in `index.html` is the only reliable synchronous approach in a CRA (Create React App) setup.
- **Using MUI `bgcolor` shorthand for CSS variables:** MUI's `bgcolor` shorthand routes through the palette system. Use `backgroundColor: 'var(--token)'` in the `sx` object directly.
- **Duplicating `.pct-badge` and `.section-label` definitions:** Both classes are defined in both `App.css` (global) and `CompanyPage.css` (local duplicate). The global definitions in `App.css` are the authoritative ones. The duplicates in `CompanyPage.css` should be removed during the CSS refactor.
- **Leaving `.glass-card` defined in `CompanyPage.css`:** The current `.glass-card` class uses `background: rgba(255,255,255,0.03)` (near-invisible glassmorphism). Decision D-28 replaces this with flat surface treatment. The `.glass-card` class name appears in `SentimentHeatmap.js` and `SectorSentimentRow.js` as well. All uses should be replaced with a new `.surface-card` utility class (or inline style) using the standard surface treatment from D-29.

---

## Hardcoded Color Audit

Complete inventory of hardcoded hex values found in the codebase, organized by file. Each entry shows the current value and the CSS variable replacement.

### App.css

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.section-label` color | `#94a3b8` | `var(--text-secondary)` |
| `.pct-badge--up` background | `rgba(22, 163, 74, 0.15)` | keep (sentiment colors fixed per D-18) |
| `.pct-badge--up` color | `#4ade80` | `var(--color-positive)` |
| `.pct-badge--down` background | `rgba(220, 38, 38, 0.15)` | keep (sentiment colors fixed) |
| `.pct-badge--down` color | `#f87171` | `var(--color-negative)` |

### TopBar.css

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.header` background-color | `rgb(0, 0, 0)` | `var(--bg-surface)` |
| `h1` color | `rgb(247,105,0)` | REMOVE (logo replaced with text span) |
| `.custom-sentiment-button` background-color | `#f60` | `var(--accent-blue)` |
| `.custom-sentiment-button:hover` background-color | `#e55` | darken accent (or filter: brightness(0.85)) |
| `.last-updated-text` color | `#94a3b8` | `var(--text-secondary)` |

Add to `.header`:
```css
border-bottom: 1px solid var(--border);
```

### SentimentHeatmap.css

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.heatmap-tooltip` background | `#1e293b` | `var(--bg-surface)` |
| `.heatmap-tooltip` border color | `rgba(255,255,255,0.1)` | `var(--border)` |
| `.tooltip-price` color | `#94a3b8` | `var(--text-secondary)` |
| `.tooltip-sentiment` color | `#94a3b8` | `var(--text-secondary)` |
| `.heatmap-error, .heatmap-empty` color | `#94a3b8` | `var(--text-secondary)` |

### SentimentHeatmap.js (inline `style` in JSX)

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| Skeleton div background | `rgba(255,255,255,0.08)` | `var(--bg-elevated)` |

Note: The heatmap cell colors (`#16a34a`, `#4ade80`, `#475569`, `#f87171`, `#dc2626`) in `getSentimentColor()` are **sentiment palette values locked in Phase 5 (D-09 of 05-CONTEXT.md)** — do NOT replace with CSS variables. These are data-driven visual encodings, not theme colors.

### SectorSentimentRow.css

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.sector-count` color | `#94a3b8` | `var(--text-secondary)` |
| `.sector-row-error` color | `#94a3b8` | `var(--text-secondary)` |

### SectorSentimentRow.js (sx props)

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| Skeleton `bgcolor` | `rgba(255,255,255,0.08)` | `sx={{ backgroundColor: 'var(--bg-elevated)' }}` |
| Retry Button `color` | `#94a3b8` | `sx={{ color: 'var(--text-secondary)' }}` |
| Retry Button `borderColor` | `#475569` | `sx={{ borderColor: 'var(--text-disabled)' }}` |

`getSentimentColor()` return values (`#16a34a`, `#4ade80`, `#f87171`, `#dc2626`, `#475569`) in SectorSentimentRow.js are sentiment data colors — do NOT replace.

### CompanyPage.css

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.glass-card` background | `rgba(255,255,255,0.03)` | `var(--bg-surface)` (D-28 removes glassmorphism) |
| `.glass-card` border | `rgba(255,255,255,0.05)` | `var(--border)` |
| `.chart-section h3` color | `#94a3b8` | `var(--text-secondary)` |
| `.metric-card span` color | `#94a3b8` | `var(--text-secondary)` |
| `.loading-spinner` color | `#94a3b8` | `var(--text-secondary)` |
| `.narrative-text` color | `#cbd5e1` | `var(--text-primary)` (closest semantic match) |
| `.narrative-staleness` color | `#94a3b8` | `var(--text-secondary)` |
| `.narrative-pending-caption` color | `#94a3b8` | `var(--text-secondary)` |
| `.narrative-error` color | `#94a3b8` | `var(--text-secondary)` |
| `.chart-error` color | `#94a3b8` | `var(--text-secondary)` |
| `.price-change.up` color | `#10b981` | `var(--color-positive)` |
| `.price-change.down` color | `#ef4444` | `var(--color-negative)` |
| `.pct-badge` (duplicate) | various | REMOVE — use global `.pct-badge` from `App.css` |
| `.section-label` (duplicate) | `#94a3b8` | REMOVE — use global `.section-label` from `App.css` |

### CompanyPage.js (sx props)

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| Skeleton `bgcolor` (chart) | `rgba(255,255,255,0.08)` | `sx={{ backgroundColor: 'var(--bg-elevated)' }}` |
| Skeleton `bgcolor` (narrative) | `rgba(255,255,255,0.08)` | `sx={{ backgroundColor: 'var(--bg-elevated)' }}` |
| Retry Button `color` | `#94a3b8` | `sx={{ color: 'var(--text-secondary)' }}` |
| Retry Button `borderColor` | `#475569` | `sx={{ borderColor: 'var(--text-disabled)' }}` |
| ComposedChart CartesianGrid stroke | `rgba(255,255,255,0.07)` | Can leave as-is (data ink, not theme color) OR use `var(--border)` |
| XAxis/YAxis stroke and tick fill | `#94a3b8` | Leave as inline prop values — Recharts does not consume CSS variables via SVG attributes |
| Tooltip `contentStyle` backgroundColor | `#1e293b` | `var(--bg-surface)` — valid in Recharts contentStyle object |

**Recharts SVG attributes note:** SVG attributes like `stroke="#94a3b8"` on `<XAxis>` do NOT inherit CSS variables. SVG `stroke` and `fill` attributes (not CSS properties) bypass the CSS cascade. These must be set either as hardcoded strings or read from a JS constant. Recommendation: Create a JS constants object `CHART_COLORS` in a `theme.js` utility file that mirrors the token values — import it wherever Recharts props need color values. This avoids `getComputedStyle` calls but does not auto-switch on theme toggle.

### TopBar.js (sx props) — Full inventory

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `LinearProgress` backgroundColor | `rgba(59,130,246,0.2)` | `rgba(59,130,246,0.2)` — keep (accent blue is theme-stable per D-18) |
| `LinearProgress` bar backgroundColor | `#3b82f6` | `var(--accent-blue)` |
| SettingsIcon `color` | `#94a3b8` | `var(--text-secondary)` |
| Dialog `PaperProps` backgroundColor | `#1e293b` | `var(--bg-surface)` |
| Dialog `PaperProps` color | `#f1f5f9` | `var(--text-primary)` |
| DialogTitle color | `#f1f5f9` | `var(--text-primary)` |
| DialogTitle borderBottom | `1px solid rgba(255,255,255,0.08)` | `1px solid var(--border)` |
| InputLabel color | `#cbd5e1` | `var(--text-secondary)` |
| InputLabel `Mui-focused` color | `#93c5fd` | `var(--accent-blue)` |
| InputLabel `backgroundColor` | `#1e293b` | `var(--bg-surface)` |
| Select color | `#f1f5f9` | `var(--text-primary)` |
| Select outline borderColor | `#475569` | `var(--text-disabled)` |
| Select hover borderColor | `#94a3b8` | `var(--text-secondary)` |
| Select focused borderColor | `#93c5fd` | `var(--accent-blue)` |
| Select icon color | `#94a3b8` | `var(--text-secondary)` |
| MenuItem backgroundColor | `#1e293b` | `var(--bg-surface)` |
| MenuItem color | `#f1f5f9` | `var(--text-primary)` |
| MenuItem hover backgroundColor | `#334155` | `var(--bg-elevated)` |
| MenuItem selected backgroundColor | `#1d4ed8` | (keep specific blue — selected state) |
| DialogActions borderTop | `rgba(255,255,255,0.08)` | `var(--border)` |
| Cancel Button color | `#94a3b8` | `var(--text-secondary)` |
| Save Button backgroundColor | `#3b82f6` | `var(--accent-blue)` |

### StockChart.css (ticker strip)

| Location | Current Value | Replace With |
|----------|---------------|--------------|
| `.ticker-strip` background-color | `#0f172a` | `var(--bg-page)` |
| `.ticker-strip` border-top | `rgba(255, 255, 255, 0.1)` | `var(--border)` |

### NewsData.css / NewsData.js

Full rewrite per D-25. No hex values to migrate (current file has no hardcoded colors). The new layout introduces all CSS variable references from the start.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Theme toggle with FOUC prevention | Custom React hydration logic | Inline `<script>` in `index.html` + `data-theme` on `<html>` | This is the canonical pattern; React cannot reliably prevent FOUC since it renders client-side after HTML parse |
| Recharts SVG color switching | Dynamic `getComputedStyle` calls on every render | JS constants object mirroring theme tokens | `getComputedStyle` is expensive and creates render dependencies; static constants are sufficient for chart colors |
| CSS variable switching animation | JS `requestAnimationFrame` transitions | CSS `transition: background-color 200ms ease, color 200ms ease` on `:root` or `body` | Browser handles the interpolation natively with zero JS |

**Key insight:** All the hard problems in theme switching (FOUC, SVG color limits, transition smoothness) have well-established solutions that don't require custom logic. The inline script pattern is used by next-themes, gatsby-plugin-dark-mode, and every major theming library.

---

## Common Pitfalls

### Pitfall 1: FOUC on Hard Reload
**What goes wrong:** React reads `localStorage` in a `useEffect` or `useState` initializer, sets `data-theme` after the first render. For one frame, `:root` (dark) styles apply, then the theme switches — visible as a flash of dark-on-dark or incorrect colors.
**Why it happens:** React is client-side. `useEffect` and `useState` run after the HTML document has been parsed and the first paint has occurred.
**How to avoid:** Blocking inline `<script>` in `public/index.html` inside `<head>`. Runs synchronously before any HTML is rendered.
**Warning signs:** Opening app in a new tab after setting light mode shows dark background for <100ms.

### Pitfall 2: MUI `bgcolor` Shorthand Ignores CSS Variables
**What goes wrong:** `<Skeleton sx={{ bgcolor: 'var(--bg-elevated)' }} />` renders the skeleton as invisible (transparent) or with wrong color because MUI's `bgcolor` shorthand resolves through its theme palette, not raw CSS.
**Why it happens:** MUI's System shortcuts (`bgcolor`, `color`, `borderColor`) map to the MUI palette before CSS. String values that don't match palette paths are dropped or fall back to `transparent`.
**How to avoid:** Use `sx={{ backgroundColor: 'var(--bg-elevated)' }}` — the full CSS property name bypasses MUI's palette resolution and passes the value directly to CSS.
**Warning signs:** Skeletons invisible in light mode, or appear as solid black/transparent rectangles.

### Pitfall 3: Recharts SVG Attributes Don't Inherit CSS Variables
**What goes wrong:** Setting `stroke="var(--text-secondary)"` on `<XAxis>` renders as the literal string — no color.
**Why it happens:** SVG `stroke` and `fill` are XML attributes in SVG context, not CSS properties. CSS custom properties only work when the browser resolves a CSS property — SVG attributes set directly in JSX bypass the CSS engine entirely.
**How to avoid:** Use a `CHART_THEME` JS object with hardcoded color values. Accept that chart axis colors won't auto-switch on theme toggle (acceptable for this phase — chart data ink colors like sentiment bars and price area are not theme colors).
**Warning signs:** Axis labels disappear or show placeholder text in theme switch.

### Pitfall 4: `.glass-card` Class Used in Multiple Components
**What goes wrong:** Renaming/replacing `.glass-card` in `CompanyPage.css` doesn't affect `SentimentHeatmap.js` and `SectorSentimentRow.js` which also apply `className="... glass-card"`.
**Why it happens:** The `.glass-card` class is defined only in `CompanyPage.css` but used by components that don't import that CSS file — they inherit the style through CSS global scope (all Create React App CSS is global).
**How to avoid:** Audit all `glass-card` uses in JSX before removing the class definition. Replace with a new `.surface-card` utility class defined in `App.css` (global scope, intentionally).
**Warning signs:** Heatmap or sector cards lose background styling after CompanyPage.css refactor.

### Pitfall 5: Duplicate `.pct-badge` and `.section-label` in CompanyPage.css
**What goes wrong:** The duplicate definitions in `CompanyPage.css` override the global ones from `App.css` for elements inside `.company-page`, potentially diverging after the refactor.
**Why it happens:** The duplicates were added before the global versions existed, and were never cleaned up.
**How to avoid:** Remove the duplicate definitions from `CompanyPage.css` during the refactor. Verify the global `App.css` versions apply correctly to CompanyPage elements.
**Warning signs:** Section labels or percent badges look different on CompanyPage vs. HomePage after the refactor.

### Pitfall 6: `--bg-elevated` Not Visible for Skeleton in Light Mode
**What goes wrong:** If `--bg-elevated` in light mode is `#f1f5f9` and the card surface is `#ffffff`, the skeleton on a white card may have very low contrast.
**Why it happens:** Light theme surfaces are near-white; the elevated color is slightly grey — contrast ratio is small but sufficient. However, using `backgroundColor` on Skeleton (not `bgcolor`) is required first.
**How to avoid:** Verify skeleton visibility in both themes during implementation. `#f1f5f9` on `#ffffff` has sufficient contrast for a loading animation. If contrast is too low, `--bg-elevated` in light mode can be adjusted to `#e2e8f0` without breaking any locked decisions (it's within Claude's discretion).

---

## Code Examples

### FOUC Prevention Script
```html
<!-- public/index.html — place inside <head>, after the last <meta> tag -->
<script>
  (function() {
    var theme = localStorage.getItem('sentiment_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  })();
</script>
```
Source: Standard pattern used by next-themes, gatsby-plugin-dark-mode, Josh Comeau's CSS-for-JS course — verified against multiple authoritative sources. HIGH confidence.

### Theme Toggle Handler in StockDataContext
```javascript
// Add to StockDataContext.js
const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('sentiment_theme') || 'dark';
});

const setTheme = useCallback((newTheme) => {
    localStorage.setItem('sentiment_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    setThemeState(newTheme);
}, []);

// Sync attribute on first mount (belt-and-suspenders; inline script handles this too)
useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

### Theme Toggle Button in Settings Dialog
```jsx
// Inside the existing <DialogContent> in TopBar.js, below the FormControl for refresh interval
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';

// In the render:
const { theme, setTheme } = useContext(StockDataContext);

<Box sx={{ mt: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        Theme
    </Typography>
    <IconButton
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        size="small"
        sx={{ color: 'var(--text-secondary)' }}
        aria-label="Toggle theme"
    >
        {theme === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
    </IconButton>
</Box>
```

### CSS Transition for Smooth Theme Switch
```css
/* Add to App.css body rule or :root */
body {
    background-color: var(--bg-page);
    color: var(--text-primary);
    transition: background-color 200ms ease, color 200ms ease;
}
```

### Surface Card Utility Class (replacing .glass-card)
```css
/* Add to App.css — global utility, replaces .glass-card everywhere */
.surface-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}
```

### Recharts Chart Colors JS Object
```javascript
// src/utils/chartTheme.js — new utility file
export const CHART_THEME = {
    axisColor: '#94a3b8',       // --text-secondary dark value; acceptable to hardcode for charts
    gridColor: 'rgba(255,255,255,0.07)',
    tooltipBg: '#1e293b',       // --bg-surface dark value
    priceStroke: '#3b82f6',     // --accent-blue (same both themes)
    sentimentPos: '#4ade80',    // --color-positive (same both themes)
    sentimentNeg: '#f87171',    // --color-negative (same both themes)
};
```
Note: Chart axis colors are hardcoded to dark-mode values. Recharts SVG attributes cannot use CSS variables. This is an acceptable limitation for Phase 6 scope.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MUI `styled()` + `ThemeProvider` for theming | CSS custom properties + `data-theme` attribute | Industry shift ~2020–2022 | Zero JS cost for theme switching; CSS handles cascade; no re-render on toggle |
| `body.dark-mode` class switching | `html[data-theme="dark"]` attribute | ~2021+ | `<html>` is preferred because it covers the full document including `<head>` styles and `:root` |
| `prefers-color-scheme` media query only | `prefers-color-scheme` + localStorage override | Current best practice | `prefers-color-scheme` is the fallback; user override stored in localStorage takes precedence |

**Deprecated/outdated:**
- `document.body.classList.add('dark')`: Lower specificity than attribute-on-html; misses some edge cases in document-level styles.
- MUI v4 `makeStyles`/`withStyles`: Already removed in Phase 1/Phase 5; project uses `sx` props throughout.

---

## Open Questions

1. **Recharts axis colors in light mode**
   - What we know: SVG attributes cannot use CSS variables; chart axis labels will remain `#94a3b8` in both themes.
   - What's unclear: Whether light-mode users will find grey-on-white axis labels readable enough.
   - Recommendation: Accept the limitation for Phase 6. If visibility is poor in light mode, add a `useContext(StockDataContext)` call in chart components to read `theme` and conditionally set axis colors — that's a trivial follow-up.

2. **News thumbnail availability**
   - What we know: `NewsItem.js` currently reads `news.thumbnail?.resolutions[0]?.url` — this can be `null` if no thumbnail is provided by the API.
   - What's unclear: What percentage of articles from the backend news API have thumbnails.
   - Recommendation: Use a CSS `background: var(--bg-elevated)` placeholder on the `<img>` container, plus `onerror` fallback to hide the broken image. The card layout should degrade gracefully (text-only) if no image is available.

3. **`var(--bg-elevated)` as Skeleton backgroundColor in MUI**
   - What we know: MUI Skeleton renders the `sx.backgroundColor` value as a CSS `background-color` property. CSS variables are valid CSS property values.
   - What's unclear: Whether MUI's animation (`animation="wave"`) applies correctly when `backgroundColor` is a CSS variable (the wave animation uses a linear-gradient overlay).
   - Recommendation: Implement and visually verify. If the wave animation disappears, fall back to `animation="pulse"` which doesn't rely on background manipulation.

---

## Environment Availability

Step 2.6: SKIPPED — This phase is purely CSS/JS code changes with no external dependencies beyond the existing Node/React/MUI stack already installed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None configured at frontend level (CRA test runner = Jest + React Testing Library available but no test files exist for Phase 6 scope) |
| Config file | None — Phase 8 introduces automated test suite |
| Quick run command | `cd frontend/stock_sentiment_analysis && npm test -- --watchAll=false` |
| Full suite command | `cd frontend/stock_sentiment_analysis && npm test -- --watchAll=false --coverage` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIS-01 | CSS variables defined and resolve correctly | manual-only | — | N/A |
| VIS-02 | No FOUC on theme reload | manual-only | — | N/A |
| VIS-03 | Theme toggle persists across reload | manual-only | — | N/A |
| VIS-04 | App title shows "StockSentimentSense", no logo image | visual | — | N/A |
| VIS-05 | TopBar uses surface background, has bottom border | visual | — | N/A |
| VIS-06 | All CSS files use var() references, no hardcoded hex | grep audit | `grep -r "#[0-9a-fA-F]\{3,6\}" src/components` | N/A |
| VIS-07 | MUI sx props use var() references | grep audit | `grep -r "sx={{" src/components` | N/A |
| VIS-08 | News renders as card grid with hero + 3-column | visual | — | N/A |
| VIS-09 | Skeletons visible in both themes | visual | — | N/A |
| VIS-10 | Consistent surface treatment across all pages | visual | — | N/A |

**Note:** Phase 6 is a pure visual phase. All requirements are verified by visual inspection (UAT) rather than automated tests. The grep audit for VIS-06 and VIS-07 is the only automatable verification step — run it at the end of the CSS refactor task to catch any missed hardcoded values.

### Sampling Rate
- **Per task commit:** Run grep audit for lingering hex values in modified CSS files
- **Per wave merge:** Full visual review of dark + light themes across all 3 pages (HomePage, CompanyPage, CustomSentiment)
- **Phase gate:** Visual UAT checklist (all 10 VIS-XX items) before `/gsd:verify-work`

### Wave 0 Gaps
None — no automated test infrastructure needed for this visual phase.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase audit — all 8 CSS files and 5 JS components read and inventoried
- CSS Custom Properties specification (MDN) — cascade behavior of `:root` and `[data-theme]` attribute selectors
- MUI v5 `sx` prop documentation — string CSS values pass through to CSS without palette resolution

### Secondary (MEDIUM confidence)
- FOUC prevention pattern (inline blocking script) — widely documented in next-themes README, Josh Comeau's blog, css-tricks.com; verified as the standard CRA approach
- SVG attribute CSS variable limitation — documented in MDN SVG attribute reference; confirmed that `stroke` as SVG attribute does not resolve CSS custom properties

### Tertiary (LOW confidence)
- MUI Skeleton wave animation compatibility with CSS variable `backgroundColor` — not explicitly documented; flagged as Open Question 3 for visual verification during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing tech
- Architecture: HIGH — CSS custom property pattern is well-established; full codebase audit completed
- Pitfalls: HIGH for FOUC (widely documented), HIGH for MUI bgcolor shorthand (documented MUI behavior), MEDIUM for Recharts SVG (confirmed by spec, practical behavior should match)
- Color audit: HIGH — complete inventory from direct source read

**Research date:** 2026-03-30
**Valid until:** 2026-06-30 (stable CSS/React patterns; MUI v5 API unlikely to change)

---

## RESEARCH COMPLETE
