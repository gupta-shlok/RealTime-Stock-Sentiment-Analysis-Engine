# Phase 5: UI Overhaul & Polish — Research

**Researched:** 2026-03-28
**Domain:** React frontend — Recharts 2.12, MUI v5, React Context refactor
**Confidence:** HIGH (verified against Recharts GitHub source and MUI official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Heatmap is the hero element at the top of the homepage; replaces scrolling ticker strip in main content area.
- **D-02:** Homepage vertical order: Heatmap → Sector Sentiment summary row → Latest News feed.
- **D-03:** Fixed horizontal ticker strip pinned to bottom of viewport (`position: fixed; bottom: 0`). `padding-bottom: 48px` added to page body.
- **D-04:** Existing `StockChart` component repurposed into fixed bottom bar. Shows ticker symbol, current price, percent change for all 100 stocks in auto-scrolling marquee.
- **D-05:** Stocks in sectors with `stock_count >= 3` grouped under GICS sector label.
- **D-06:** Stocks from sectors with `stock_count < 3` (Real Estate: EQIX, SPG — 2 stocks) grouped under "OTHER" label at end of heatmap. All 100 stocks visible.
- **D-07:** "OTHER" group renders with same cell styling but muted label color (`#64748b`) to distinguish from GICS sectors.
- **D-08:** Cells sized by `market_cap` from `tickers.py` `TICKER_DATA`.
- **D-09:** 5-stop diverging palette: `#16a34a` → `#4ade80` → `#475569` → `#f87171` → `#dc2626`. Breakpoints at -1.0, -0.4, 0.0, +0.4, +1.0.
- **D-10:** Heatmap does NOT re-animate on every polling cycle — Recharts `<Treemap>` data reference updated in-place.
- **D-11:** Auto-refresh uses `useInterval` custom hook. Polling pauses when `document.visibilityState === 'hidden'`.
- **D-12:** Settings gear icon in TopBar opens MUI `<Dialog>` modal. Contains refresh interval selector (5 min / 10 min / 30 min; default 10 min).
- **D-13:** During refresh: 2px MUI `<LinearProgress>` at top of page. Timestamp swaps to "Updating…". No unmount/remount.
- **D-14:** After refresh: timestamp updates to "Last updated HH:MM" in 12-hour format.
- **D-15:** Existing `CompanyPage.js` retrofitted (not rewritten). `/stock/:ticker` route added to `App.js`.
- **D-16:** Dual-axis `<ComposedChart>`: price as `<Area>` on left Y-axis; per-day sentiment as `<Bar>` with per-cell `<Cell>` coloring on right Y-axis (domain -1 to 1).
- **D-17:** Dual-axis chart stays mounted during background refresh — only data prop updated.
- **D-18:** Below Qwen narrative: muted caption "Generated X min ago" from `generated_at` timestamp.
- **D-19:** Pending narrative state shows `<Skeleton animation="wave">` placeholder while polling.
- **D-20:** All data-dependent components show `<Skeleton animation="wave">` while loading.
- **D-21:** Dark theme skeleton: `bgcolor` overridden to `rgba(255,255,255,0.08)`.
- **D-22:** Per-component inline error state (not full-page). Shows: which endpoint failed + "Retry" button.
- **D-23:** Percent-change figures as color-tinted pill badges. `font-variant-numeric: tabular-nums` on all price/change numbers.
- **D-24:** Section labels: `text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.75rem`.
- **D-25:** Dark glassmorphism CSS theme (`glass-panel`, `glass-card`) preserved and extended — no visual identity change.

### Claude's Discretion

- Exact Recharts `<Treemap>` `content` render prop implementation for sector labels and cell coloring
- How `StockDataContext` is refactored to expose `{ data, loading, error, lastUpdated, refresh }` — implementation detail
- Tooltip design for heatmap cells (what info to show on hover)
- Mobile/tablet breakpoints for responsive layout (UI-08)
- Exact polling behavior when a refresh is already in-flight (skip or queue)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Sentiment heatmap via Recharts `<Treemap>` — 100 stocks, sized by market cap, 5-stop diverging palette | Treemap `content` render prop pattern confirmed; `dataKey` drives cell size; `isAnimationActive={false}` + stable `useMemo` reference controls re-animation |
| UI-02 | Stocks grouped by GICS sector, sector label overlay when `stock_count >= 3` | Nested `children` array data format confirmed; sector node depth=0, stock cells depth=1; SVG `<text>` rendered inside sector bounds via `content` prop |
| UI-03 | Price + sentiment dual-axis `<ComposedChart>` — `<Area>` left Y, `<Bar>` with `<Cell>` coloring right Y, domain -1 to 1 | `yAxisId` prop confirmed on `<YAxis>`, `<Area>`, `<Bar>`; `<Cell>` fills inside `<Bar>` confirmed; domain prop on `<YAxis>` confirmed |
| UI-04 | Auto-refresh with configurable polling interval (default 10 min); `useInterval` hook; chart stays rendered | `useInterval` pattern with `useRef` + `useEffect` confirmed; visibility API integration pattern confirmed; in-flight guard via `isRefreshing` ref |
| UI-05 | Last-updated timestamp visible, swaps to "Updating…" during refresh | `isRefreshing` boolean in context drives conditional display; `toLocaleTimeString` with `hour12: true` for 12-hour format |
| UI-06 | Skeleton loaders for all data-dependent components — MUI `<Skeleton animation="wave">` with dark-theme `bgcolor` override | `sx={{ bgcolor: 'rgba(255,255,255,0.08)' }}` on `<Skeleton>` confirmed; `animation="wave"` confirmed |
| UI-07 | Informative error states (not blank screens) for all fetch failures | Per-component error boundary pattern; `error` string in context; `<Button variant="outlined" size="small">Retry</Button>` |
| UI-08 | Responsive layout — usable on tablet and desktop | Existing `@media (max-width: 768px)` in CompanyPage.css is the breakpoint anchor; CSS Grid `auto-fit` already used |
| UI-09 | Typography — section labels all-caps with letter-spacing; price numbers with tabular-nums | CSS class `.section-label` for the upgrade; `font-variant-numeric: tabular-nums` already on `JetBrains Mono` numeric elements |
| UI-10 | Percent change as color-tinted pill badge (not just colored text) | `<span class="pct-badge pct-badge--up/down">` pattern; CSS `border-radius: 9999px; padding: 2px 8px` |
</phase_requirements>

---

## Summary

Phase 5 is a pure frontend build atop a completed backend. All Phase 4 endpoints are live (`/stock-price`, `/sentiment-trends`, `/sector-sentiment`, `/stock-narrative/{ticker}`). The existing React codebase is a Create React App project with MUI v5 and Recharts 2.12.3 already installed. No new packages are needed.

The central task is a `StockDataContext` refactor (currently returns a flat array with no loading/error/refresh state) and three major new components: the Treemap heatmap, the dual-axis ComposedChart, and the fixed bottom ticker strip. The existing `CompanyPage.js`, `TopBar.js`, `HomePage.js`, `StockChart.js`, and `StockDetails.js` are all retrofit targets — not rewrites.

The main technical risk is Recharts Treemap re-animation on data updates. Issue #1281 in the Recharts repo confirmed that `isAnimationActive={false}` is unreliable when the data reference changes. The correct mitigation is `isAnimationActive={false}` combined with a stable `useMemo` reference that mutates cell values in-place rather than producing a new array on each poll cycle.

**Primary recommendation:** Implement in this dependency order: (1) `StockDataContext` refactor, (2) new API functions in `api.js`, (3) `useInterval` hook, (4) heatmap component, (5) dual-axis chart, (6) fixed ticker strip retrofit, (7) skeleton/error/badge polish, (8) settings modal, (9) route + CompanyPage retrofit.

---

## Standard Stack

### Core (already installed — no `npm install` needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 2.12.3 | Treemap, ComposedChart, Area, Bar, Cell, YAxis | Already in package.json; project-locked |
| @mui/material | ^5.15.14 | Skeleton, LinearProgress, Dialog, Select, Button, IconButton | Already in package.json; project-locked |
| @mui/icons-material | (bundled with MUI v5) | SettingsIcon for TopBar gear | Already available via MUI v5 |
| react-router-dom | ^6.22.3 | `useParams` for `/stock/:ticker` route | Already in package.json |
| axios | ^1.6.8 | API calls for new endpoints | Already in api.js |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @emotion/react | ^11.11.4 | MUI v5 peer dep; `sx` prop support | Already installed; needed for MUI theming |
| @emotion/styled | ^11.11.5 | MUI v5 peer dep | Already installed |

### No New Packages

Zero new packages are required. `@mui/icons-material` is included in the MUI v5 bundle already present. The `SettingsIcon` is accessible via `import SettingsIcon from '@mui/icons-material/Settings'`.

**Verification:** `package.json` at `frontend/stock_sentiment_analysis/package.json` confirms all versions. `node_modules` directory is not present in the repo (must run `npm install` before development, normal for a git repo).

---

## Architecture Patterns

### Current Context Shape (BEFORE refactor)

```javascript
// StockDataContext.js — CURRENT (flat array, no loading/error/refresh)
export const StockDataContext = createContext([]);
// Provider value: stockArray (flat array of {name, current_close, previous_close, percent_change, history})
// Callers: useContext(StockDataContext) returns this array directly
```

### Existing consumers that depend on the current context shape

| Component | How it reads context | Refactor impact |
|-----------|---------------------|-----------------|
| `StockChart.js` | `const stockData = useContext(StockDataContext)` — iterates `stockData.map()` | Must update to read from new shape |
| `CompanyPage.js` | `const stockData = useContext(StockDataContext)` — calls `stockData.find()` | Must update to read from new shape |
| `TopCompanies.js` | `const stockData = useContext(StockDataContext)` — calls `stockData.sort()` | Must update to read from new shape |

**Critical:** All three consumers call array methods directly on the context value. After the refactor, context value becomes an object `{ stocks, loading, error, lastUpdated, isRefreshing, refresh }`. Each consumer must be updated to use `stocks` instead of the context value directly.

### Refactored Context Shape (AFTER)

```javascript
// StockDataContext.js — TARGET
// Context value: { stocks, loading, error, lastUpdated, isRefreshing, refresh }
// stocks: same flat array as before (each item: {name, sector, current_close, previous_close, percent_change, history})
// loading: true only on first load (no data yet)
// isRefreshing: true during background polls (data already present)
// error: null or error message string
// lastUpdated: Date object or null
// refresh: function to manually trigger a re-fetch

export const StockDataContext = createContext({
  stocks: [],
  loading: true,
  error: null,
  lastUpdated: null,
  isRefreshing: false,
  refresh: () => {},
});
```

### New API Functions Needed

The current `api.js` only has `getStockData()` (calls `/stock-price`) and `getNewsData()` (calls `/news`). Phase 5 needs three more:

```javascript
// Add to api.js:
export const getSentimentTrends = (ticker, window = '7d') => { /* GET /sentiment-trends */ }
export const getSectorSentiment = () => { /* GET /sector-sentiment */ }
export const getStockNarrative = (ticker) => { /* GET /stock-narrative/{ticker} */ }
```

**Authentication note (CONFIRMED):** Header name is `X-API-Key` (confirmed: `APIKeyHeader(name="X-API-Key")` at main.py line 302). Axios calls to authenticated endpoints must include `headers: { "X-API-Key": process.env.REACT_APP_API_KEY }`. The `/stock-price` and `/news` endpoints are public. Local dev bypasses key check when `settings.api_key == "dev-key-optional"`.

### Pattern 1: Recharts Treemap with Custom Content

**What:** `<Treemap>` accepts a `content` prop — either a React element (cloned with node props) or a function called per node. Use it to render SVG `<rect>` + `<text>` with per-cell color interpolation and sector labels.

**Data format for sector grouping (nested children):**

```javascript
// Source: Recharts GitHub recharts/recharts, Treemap.tsx 2.x branch
// When 'children' property is present, treated as nested treemap
const heatmapData = [
  {
    name: 'Technology',   // sector name — depth=0 node
    children: [
      { name: 'AAPL', size: 3656844050432, sentiment: 0.42 },
      { name: 'NVDA', size: 4071573684224, sentiment: 0.78 },
      // ... all tech stocks
    ]
  },
  {
    name: 'OTHER',        // sub-threshold sectors merged here
    children: [
      { name: 'EQIX', size: 94619492352, sentiment: -0.12 },
      { name: 'SPG',  size: 58553331712, sentiment: 0.05 },
    ]
  },
  // ... other sectors
];
```

**Content render prop — confirmed signature:**

From Recharts source (`Treemap.tsx` 2.x, `renderNode()` method):
```javascript
const nodeProps = { ...filterProps(this.props, false), ...node, root };
```
The custom content component/function receives:
- `x`, `y`, `width`, `height` — SVG rectangle bounds
- `depth` — 0 for sector root nodes, 1 for leaf (stock) nodes
- `name` — the `nameKey` field (defaults to `name`)
- `value` — the computed treemap value (proportional area)
- `root` — reference to the root node
- `index` — sibling index
- All additional data fields from the original data object (e.g., `sentiment`, `size`)

```javascript
// Source: Recharts GitHub demo/component/Treemap.tsx 2.x — DemoTreemapItem pattern
const CustomTreemapContent = (props) => {
  const { x, y, width, height, depth, name, sentiment } = props;

  if (depth === 0) {
    // Sector root node — render label only, no fill (transparent or border)
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} fill="none"
              stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        {width > 60 && height > 20 && (
          <text x={x + width / 2} y={y + 14} textAnchor="middle"
                fill="#94a3b8" fontSize={11} fontWeight={700}
                style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {name}
          </text>
        )}
      </g>
    );
  }

  // Leaf node (stock cell)
  const fill = interpolateSentimentColor(sentiment ?? 0);
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill}
            stroke="rgba(10,10,15,0.3)" strokeWidth={1} />
      {width > 40 && (
        <text x={x + width / 2} y={y + height / 2} textAnchor="middle"
              dominantBaseline="middle" fill="#fff" fontSize={10} fontWeight={700}>
          {name}
        </text>
      )}
    </g>
  );
};
```

**When to use:** Any time you need per-cell colors, labels, or hover state on the Treemap.

### Pattern 2: 5-Stop Diverging Color Interpolation

**What:** Linear interpolation between 5 stops keyed at -1.0, -0.4, 0.0, +0.4, +1.0.

```javascript
// Source: CONTEXT.md D-09, REQUIREMENTS.md UI-01
const SENTIMENT_STOPS = [
  { score: -1.0, color: [220, 38, 38]  },   // #dc2626
  { score: -0.4, color: [248, 113, 113] },  // #f87171
  { score:  0.0, color: [71, 85, 105]  },   // #475569
  { score:  0.4, color: [74, 222, 128] },   // #4ade80
  { score:  1.0, color: [22, 163, 74]  },   // #16a34a
];

function interpolateSentimentColor(score) {
  const clamped = Math.max(-1, Math.min(1, score));
  // Find surrounding stops
  let lo = SENTIMENT_STOPS[0], hi = SENTIMENT_STOPS[SENTIMENT_STOPS.length - 1];
  for (let i = 0; i < SENTIMENT_STOPS.length - 1; i++) {
    if (clamped >= SENTIMENT_STOPS[i].score && clamped <= SENTIMENT_STOPS[i + 1].score) {
      lo = SENTIMENT_STOPS[i];
      hi = SENTIMENT_STOPS[i + 1];
      break;
    }
  }
  const t = (clamped - lo.score) / (hi.score - lo.score);
  const r = Math.round(lo.color[0] + t * (hi.color[0] - lo.color[0]));
  const g = Math.round(lo.color[1] + t * (hi.color[1] - lo.color[1]));
  const b = Math.round(lo.color[2] + t * (hi.color[2] - lo.color[2]));
  return `rgb(${r},${g},${b})`;
}
```

### Pattern 3: Recharts ComposedChart Dual Y-Axis

**What:** `<ComposedChart>` with two `<YAxis>` components using `yAxisId`. `<Area>` and `<Bar>` each reference their axis by `yAxisId`.

```javascript
// Source: Recharts GitHub recharts.github.io/en-US/api/YAxis — yAxisId prop confirmed
// yAxisId: "Unique ID that represents this YAxis. Required when there are multiple YAxes."
import {
  ComposedChart, Area, Bar, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

<ResponsiveContainer width="100%" height={300}>
  <ComposedChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
    <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />

    {/* Left Y-axis: price */}
    <YAxis yAxisId="price" orientation="left" stroke="#3b82f6" />

    {/* Right Y-axis: sentiment — fixed domain */}
    <YAxis yAxisId="sentiment" orientation="right" domain={[-1, 1]}
           stroke="#94a3b8" tickCount={5} />

    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />

    {/* Price area — left axis */}
    <Area yAxisId="price" type="monotone" dataKey="close"
          stroke="#3b82f6" fill="rgba(59,130,246,0.1)"
          strokeWidth={2} isAnimationActive={false} />

    {/* Sentiment bars — right axis, per-bar color */}
    <Bar yAxisId="sentiment" dataKey="sentiment" isAnimationActive={false}>
      {chartData.map((entry, index) => (
        <Cell
          key={`cell-${index}`}
          fill={entry.sentiment >= 0 ? '#4ade80' : '#f87171'}
        />
      ))}
    </Bar>
  </ComposedChart>
</ResponsiveContainer>
```

**Critical:** `isAnimationActive={false}` on both `<Area>` and `<Bar>` prevents re-animation on background refresh data updates. The `<ComposedChart>` stays mounted; only `data` prop is replaced.

### Pattern 4: useInterval Hook with Visibility API

**What:** Declarative `setInterval` that pauses when the browser tab is hidden and skips ticks when a refresh is already in-flight.

```javascript
// Source: overreacted.io/making-setinterval-declarative-with-react-hooks (Dan Abramov pattern)
// Extended with visibility API and in-flight guard
import { useEffect, useRef } from 'react';

function useInterval(callback, delay) {
  const savedCallback = useRef(callback);

  // Always remember the latest callback
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    function tick() {
      if (document.visibilityState !== 'hidden') {
        savedCallback.current();
      }
    }

    const id = setInterval(tick, delay);
    return () => clearInterval(id);
  }, [delay]);
}

export default useInterval;
```

**Usage in provider:**

```javascript
// In StockDataProvider:
const isRefreshingRef = useRef(false);

useInterval(() => {
  if (isRefreshingRef.current) return; // skip if in-flight
  fetchStocks();
}, intervalMs);
```

### Pattern 5: MUI Skeleton for Dark Theme

```javascript
// Source: MUI v5 official docs — mui.com/material-ui/api/skeleton/
// bgcolor sx prop confirmed; animation="wave" confirmed

// Heatmap placeholder
<Skeleton
  variant="rectangular"
  animation="wave"
  sx={{ bgcolor: 'rgba(255,255,255,0.08)', borderRadius: '16px' }}
  height={400}
  width="100%"
/>

// Chart placeholder
<Skeleton
  variant="rectangular"
  animation="wave"
  sx={{ bgcolor: 'rgba(255,255,255,0.08)', borderRadius: '16px' }}
  height={300}
  width="100%"
/>

// Metric card placeholder
<Skeleton
  variant="rectangular"
  animation="wave"
  sx={{ bgcolor: 'rgba(255,255,255,0.08)', borderRadius: '8px' }}
  height={80}
  width="100%"
/>
```

### Pattern 6: MUI LinearProgress Fixed at Top

```javascript
// Source: MUI v5 official docs — mui.com/material-ui/api/linear-progress/
{isRefreshing && (
  <LinearProgress
    sx={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '2px',
      zIndex: 1100,
    }}
  />
)}
```

**Note:** MUI LinearProgress default `variant` is `indeterminate`, which is correct for a polling indicator. No additional props needed.

### Pattern 7: MUI Dialog Settings Modal

```javascript
// Source: MUI v5 docs — Dialog, Select pattern
import { Dialog, DialogTitle, DialogContent, DialogActions,
         Select, MenuItem, FormControl, InputLabel, Button } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';

// In TopBar:
<IconButton
  onClick={() => setSettingsOpen(true)}
  aria-label="Open settings"
  sx={{ color: '#94a3b8', '&:hover': { color: '#f76500' } }}
>
  <SettingsIcon />
</IconButton>

<Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)}
        maxWidth="xs" fullWidth>
  <DialogTitle>Settings</DialogTitle>
  <DialogContent>
    <FormControl fullWidth sx={{ mt: 1 }}>
      <InputLabel>Refresh interval</InputLabel>
      <Select value={pendingInterval} onChange={e => setPendingInterval(e.target.value)}>
        <MenuItem value={300000}>5 min</MenuItem>
        <MenuItem value={600000}>10 min</MenuItem>
        <MenuItem value={1800000}>30 min</MenuItem>
      </Select>
    </FormControl>
  </DialogContent>
  <DialogActions>
    <Button onClick={() => setSettingsOpen(false)}>Keep Current Settings</Button>
    <Button onClick={handleSave} variant="contained">Save Settings</Button>
  </DialogActions>
</Dialog>
```

**localStorage persistence:**
```javascript
const INTERVAL_KEY = 'sentiment_refresh_interval';
const DEFAULT_INTERVAL = 600000; // 10 min in ms

// Load on mount:
const stored = localStorage.getItem(INTERVAL_KEY);
const initialInterval = stored ? parseInt(stored, 10) : DEFAULT_INTERVAL;

// Save on settings confirm:
localStorage.setItem(INTERVAL_KEY, String(intervalMs));
```

### Anti-Patterns to Avoid

- **Creating a new data array on every poll:** Causes Treemap re-animation even with `isAnimationActive={false}`. Use `useMemo` or mutate the existing array structure in-place.
- **Passing `stockData` context value directly as an array:** After refactor, context value is an object. All three existing consumers (`StockChart`, `CompanyPage`, `TopCompanies`) will break silently — `.map is not a function` errors at runtime.
- **Using `type="nest"` on the Treemap:** Nest mode is interactive drill-down — clicking zooms in. The heatmap needs `type="flat"` (default) to show all 100 stocks simultaneously.
- **Putting `<Treemap>` inside `<ResponsiveContainer>` without explicit height:** Recharts Treemap requires explicit `width` and `height` props or a container with known pixel dimensions. `ResponsiveContainer` works but the inner height must be set explicitly on the Treemap (e.g., `height={400}`).
- **Using `<ComposedChart>` without `yAxisId` on data series:** Without `yAxisId`, both Area and Bar bind to the first (or only) Y-axis, making the sentiment bars invisible at stock-price scale.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interval with cleanup | manual `setInterval` in useEffect | `useInterval` custom hook | Dan Abramov pattern handles stale closure, cleanup, and dynamic delay |
| Color interpolation | ad-hoc CSS classes with if/else | `interpolateSentimentColor()` function (pure JS) | 5-stop linear interpolation is 15 lines; CSS classes cannot handle continuous scores |
| Dialog/modal | custom positioned div | MUI `<Dialog>` | Focus trapping, aria-modal, keyboard dismiss all handled |
| Loading placeholder | animated CSS shimmer | MUI `<Skeleton animation="wave">` | wave animation matches dark theme with `bgcolor` override; zero CSS to write |
| Progress indicator | custom CSS bar | MUI `<LinearProgress>` | Indeterminate animation is built-in; `sx` positioning is one prop |
| Fixed positioning clearance | JS scroll listener | `padding-bottom: 48px` on page wrapper | Pure CSS; no JS needed |

**Key insight:** Recharts and MUI together cover every visual problem in this phase. The only custom code needed is the color interpolation function and the `useInterval` hook.

---

## Critical Findings

### Finding 1: `StockDataContext` currently provides a flat array, not sector-grouped data

The current `/stock-price` endpoint returns data grouped by sector:
```json
{
  "Technology": {
    "AAPL": { "current_close": 189.3, "percent_change": 0.42, "history": [...] },
    "NVDA": { ... }
  },
  "Healthcare": { ... }
}
```

But `StockDataContext.js` immediately flattens this:
```javascript
const stockArray = Object.entries(stockData).map(([name, data]) => ({ name, ...data }));
```

This loses the sector grouping. For the heatmap, sector grouping must be re-derived. Two options:

1. **Use `TICKER_DATA` sector assignments from `tickers.py`** — the frontend equivalent must be a static map embedded in the JS (or fetched separately). The `market_cap` values are needed from this map too.
2. **Preserve sector structure from the API response** — the `/stock-price` response already has tickers grouped by sector; don't flatten it.

**Recommended:** Keep the sector grouping from the API response. Add a `stocksBySector` derived value to the context alongside the flat `stocks` array for the heatmap. The `TICKER_DATA` market_cap values must be embedded as a static JS constant in the frontend (mirror of `tickers.py`) since the backend `/stock-price` endpoint does not return `market_cap`.

### Finding 2: `/stock-price` endpoint does NOT include `market_cap` or `sector` in its response

Inspecting `main.py` lines 591–611: the response object per ticker only includes `current_close`, `previous_close`, `percent_change`, and `history`. The `market_cap` and `sector` fields from `TICKER_DATA` are NOT forwarded to the response — they are only used internally for tiered news fetching.

**Impact:** The frontend must embed a static `TICKER_META` constant (mapping ticker → `{sector, market_cap}`) mirroring `tickers.py` to construct the heatmap. This is ~100 lines of data, appropriate for a static import.

### Finding 3: Treemap re-animation is a known bug with a specific workaround

GitHub issue #1281 confirms: `isAnimationActive={false}` alone does NOT prevent Treemap re-animation when the `data` prop changes. The workaround is:
- Set `isAnimationActive={false}` on the `<Treemap>`
- Use `useMemo` to stabilize the data reference so it only updates when the data content actually changes (not on every context re-render)
- Mutate cell values in-place on the existing array rather than creating a new array

Alternatively: if animation is still triggering, set `animationDuration={0}` and `animationBegin={0}` as additional suppressors.

### Finding 4: `CompanyPage.js` reads stock data via the old context — the `/stock/:ticker` route is missing

`App.js` has no `/stock/:ticker` route. `CompanyPage.js` exists and uses `useParams()` expecting `ticker` param, but it cannot be reached. The retrofit involves two changes: add the route in `App.js` and update `CompanyPage.js` to use the refactored context shape and add the dual-axis chart + narrative section.

### Finding 5: `NewsData.js` reads from a static `news.json` file — not the live API

`NewsData.js` imports `../../news.json` (a local static file) rather than calling `getNewsData()`. The homepage news feed is currently stale/static. Phase 5 homepage should wire the news feed to the live `/news` endpoint via the context or a local fetch.

### Finding 6: Authentication for Phase 4 endpoints

`/sentiment-trends`, `/sector-sentiment`, and `/stock-narrative/{ticker}` all use `Depends(require_api_key)`. The `/stock-price` and `/news` endpoints do NOT require an API key. The frontend must include the API key header for the three authenticated endpoints. The key should be loaded from `REACT_APP_API_KEY` environment variable.

### Finding 7: `StockDetails.js` links to `href="#"` — needs update for ticker strip

The current `StockDetails` component renders `<a href="#">` with no navigation. For the fixed ticker strip repurpose, `StockDetails` (or the ticker strip component) should link to `/stock/{ticker}` so users can click through to company pages.

### Finding 8: Sector count verification — only Real Estate is below threshold

From `tickers.py` `SECTOR_TICKERS`:
- Real Estate: 2 stocks (EQIX, SPG) — BELOW threshold → goes to "OTHER"
- Basic Materials: 3 stocks (APD, DOW, LIN) — AT threshold → shown as sector
- Utilities: 3 stocks (DUK, NEE, SO) — AT threshold → shown as sector
- Energy: 4 stocks — above threshold

So "OTHER" contains only EQIX and SPG (2 stocks). LIN, APD, DOW render in their own "Basic Materials" group.

---

## Common Pitfalls

### Pitfall 1: Context refactor breaks existing consumers silently

**What goes wrong:** After changing `StockDataContext` value from a flat array to `{ stocks, loading, error, ... }`, three existing components call `.map()`, `.find()`, `.sort()` directly on the context value. These fail at runtime with "undefined is not a function" errors.
**Why it happens:** All three consumers destructure or use the context value as an array.
**How to avoid:** Update all three consumers (`StockChart.js`, `CompanyPage.js`, `TopCompanies.js`) in the same task that refactors the context. Do not refactor context without updating consumers.
**Warning signs:** Console errors "Cannot read property 'map' of undefined" immediately after context refactor.

### Pitfall 2: Treemap requires `width` and `height` as numbers, not "100%"

**What goes wrong:** `<Treemap width="100%" height={400}>` silently renders nothing or zero-size.
**Why it happens:** Unlike other Recharts charts, Treemap computes cell positions algorithmically and needs integer pixel dimensions at render time.
**How to avoid:** Always wrap in `<ResponsiveContainer>` and then pass numeric `width` and `height` to the inner `<Treemap>`, OR read `containerWidth` from `ResponsiveContainer`'s render prop. Simplest: use `<ResponsiveContainer width="100%" height={400}>` and let it inject the pixel width into the child.
**Warning signs:** Empty chart area, no error in console.

### Pitfall 3: Fixed bottom ticker strip causes content to be hidden behind it

**What goes wrong:** The last content item on the page scrolls under the 48px fixed ticker strip and cannot be read.
**Why it happens:** `position: fixed` removes the element from document flow; content below doesn't know to stop before it.
**How to avoid:** Add `padding-bottom: 48px` to the main page wrapper (not `body` — the wrapper div inside React root). If applied to `body` in index.css, it works globally but affects every page.
**Warning signs:** Last news item or chart is partially clipped by the ticker strip.

### Pitfall 4: Dual-axis chart with mismatched `yAxisId` strings

**What goes wrong:** `<Bar yAxisId="left">` with `<YAxis yAxisId="price">` — mismatched IDs. Recharts silently renders the bar on the first available axis, distorting the scale.
**Why it happens:** `yAxisId` must match exactly (string or number) between `<YAxis>` and the data series component.
**How to avoid:** Use consistent string IDs like `"price"` and `"sentiment"` on both the axis definition and the data series.
**Warning signs:** Sentiment bars appear at prices scale (e.g., bars reaching $150 instead of 0–1 range).

### Pitfall 5: API key not included in authenticated endpoint calls

**What goes wrong:** `/sentiment-trends`, `/sector-sentiment`, `/stock-narrative/{ticker}` return 403 in the frontend.
**Why it happens:** These endpoints use `Depends(require_api_key)` in FastAPI. The key header must be explicitly set in axios calls.
**How to avoid:** Add the API key as a request header in each new API function. Use `REACT_APP_API_KEY` env var. The `/stock-price` and `/news` endpoints are public — do not add the header there.
**Warning signs:** 403 responses in browser devtools network tab.

### Pitfall 6: Narrative polling loop runs indefinitely after component unmount

**What goes wrong:** When a user navigates away from a company page while the narrative is in "pending" state, the `setInterval` polling `/stock-narrative/{ticker}` continues running, causing state updates on unmounted components.
**Why it happens:** `setInterval` in `useEffect` without proper cleanup.
**How to avoid:** Return a cleanup function from the `useEffect` that sets a flag or calls `clearInterval`. Use `useEffect` return value pattern; set a `cancelled` boolean to prevent `setState` after unmount.
**Warning signs:** React console warning "Can't perform a React state update on an unmounted component."

### Pitfall 7: Heatmap tooltip shows on sector label nodes, not just stock cells

**What goes wrong:** Hovering over a sector boundary/label area triggers the Recharts tooltip, showing a sector node with no stock data.
**Why it happens:** Recharts Treemap passes tooltip props to all nodes including parent sector nodes (depth=0).
**How to avoid:** In the `<Tooltip>` `content` render prop, check if `payload[0]?.payload?.depth === 0` and return `null` to suppress the tooltip for sector nodes.
**Warning signs:** Tooltip appears blank or shows "undefined" when hovering sector boundary.

---

## Code Examples

### Building the heatmap data structure from API response + static TICKER_META

```javascript
// Source: derived from /stock-price response shape (main.py lines 591-612)
// and tickers.py SECTOR_TICKERS structure

const TICKER_META = {
  'AAPL': { sector: 'Technology', market_cap: 3656844050432 },
  'NVDA': { sector: 'Technology', market_cap: 4071573684224 },
  // ... (mirror of tickers.py TICKER_DATA)
};

// SECTOR_TICKERS from tickers.py — sectors with stock_count >= 3
// Only Real Estate (2 stocks) falls below threshold
const SUB_THRESHOLD_TICKERS = ['EQIX', 'SPG']; // Real Estate

function buildHeatmapData(stocksFlat, sentimentScores) {
  // stocksFlat: array of { name (ticker), current_close, percent_change, ... }
  // sentimentScores: object mapping ticker → score (from context or separate fetch)

  const sectorMap = {};
  const otherChildren = [];

  for (const stock of stocksFlat) {
    const ticker = stock.name;
    const meta = TICKER_META[ticker];
    if (!meta) continue;

    const cell = {
      name: ticker,
      size: meta.market_cap,  // dataKey for Treemap sizing
      sentiment: sentimentScores[ticker] ?? 0,
    };

    if (SUB_THRESHOLD_TICKERS.includes(ticker)) {
      otherChildren.push(cell);
    } else {
      if (!sectorMap[meta.sector]) sectorMap[meta.sector] = [];
      sectorMap[meta.sector].push(cell);
    }
  }

  const data = Object.entries(sectorMap).map(([sector, children]) => ({
    name: sector,
    children,
  }));

  if (otherChildren.length > 0) {
    data.push({ name: 'OTHER', children: otherChildren });
  }

  return data;
}
```

### Stable heatmap data reference (prevents re-animation)

```javascript
// In the heatmap component:
const heatmapData = useMemo(
  () => buildHeatmapData(stocks, sentimentScores),
  // Only rebuild when the actual content changes, not on every render
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [JSON.stringify(stocks?.map(s => s.name + s.percent_change))]
);
```

**Note:** `JSON.stringify` as a dependency is a code smell in general but is the pragmatic solution here for preventing Treemap re-animation. Alternative: use a deep-equality hook.

### 12-hour timestamp formatting

```javascript
// Source: MDN Web Docs — Date.toLocaleTimeString
function formatLastUpdated(date) {
  if (!date) return null;
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  // Returns: "2:34 PM"
}
```

### Narrative staleness calculation

```javascript
// Source: CONTEXT.md specifics section
function getGeneratedAgo(generatedAtISO) {
  const minutes = Math.floor((Date.now() - new Date(generatedAtISO)) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes === 1) return '1 min ago';
  return `${minutes} min ago`;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `setInterval` in useEffect | Declarative `useInterval` hook | React Hooks (2019) | Stale closure bugs eliminated |
| `component.setState` error/loading patterns | React Context with `{ data, loading, error }` shape | Widely adopted 2020+ | Single source of truth for async state |
| Recharts v1 static imports | Recharts v2 with tree-shaking | Recharts 2.x (2021) | Same API mostly; TypeScript support |
| MUI v4 `makeStyles` | MUI v5 `sx` prop / `styled` | MUI v5 (2021) | CLEAN-02 already removed v4 from this project |

**Deprecated/outdated in this codebase:**
- `NewsData.js` imports `news.json` (static file) — this is leftover from before the API existed; must be replaced with a live API call.
- `StockDetails.js` links to `href="#"` — placeholder; must route to `/stock/{ticker}`.
- `HomePage.js` renders `<StockChart />` as main content — this component becomes the fixed bottom bar; the homepage main content becomes the heatmap.

---

## Open Questions

All three initial open questions were resolved by reading `backend/main.py` during research.

1. **API key header name — RESOLVED**
   - Confirmed: `APIKeyHeader(name="X-API-Key")` at `main.py` line 302. Send as HTTP header `X-API-Key: <value>` in axios requests. Environment variable: `REACT_APP_API_KEY`.

2. **Sentiment scores for heatmap — RESOLVED (requires one backend addition)**
   - Confirmed: `/stock-price` does NOT include sentiment scores. `/sentiment-trends` is per-ticker only. `sentiment_scores.json` format is `{ "AAPL": { "2026-03-28": 0.34 } }` (main.py line 158).
   - Resolution: Plan must add a lightweight `GET /sentiment-snapshot` endpoint (loads `_load_scores_file()`, returns most-recent score per ticker as a flat dict). This is the discovered missing endpoint referenced by the phase constraint "no backend changes unless a missing endpoint is discovered." Fallback: use `percent_change` as color proxy (loses semantic accuracy).

3. **`/stock-price` response shape — RESOLVED**
   - Confirmed: Response per ticker contains only `current_close`, `previous_close`, `percent_change`, `history`. No `sentiment_score` or `market_cap` fields. Both must come from static `TICKER_META` (market_cap) and the new `/sentiment-snapshot` endpoint (sentiment scores).
---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | Frontend build | Unknown (not in PATH in this shell) | — | Must be installed on dev machine; CRA requires Node 14+ |
| recharts 2.12.3 | Treemap, ComposedChart | Listed in package.json | 2.12.3 | — (no fallback needed, already declared) |
| @mui/material 5.x | Skeleton, Dialog, LinearProgress | Listed in package.json | ^5.15.14 | — |
| @mui/icons-material | SettingsIcon | Bundled with MUI v5 | (same as @mui/material) | Use SVG inline if import fails |
| FastAPI backend | All API calls | Assumed running (Phase 4 complete) | — | Mock data for component development |

**Note:** `node_modules` directory is not present in the repo (confirmed via PowerShell `Test-Path` → False). `npm install` must be run before development. This is normal — modules are not committed to git.

---

## Validation Architecture

**nyquist_validation:** enabled (config.json `workflow.nyquist_validation: true`)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | react-scripts test (Jest + React Testing Library) — configured via CRA |
| Config file | No separate config file — Jest config embedded in `react-scripts` |
| Quick run command | `npm test -- --watchAll=false --testPathPattern="<component>"` |
| Full suite command | `npm test -- --watchAll=false` |

**Note:** CRA's Jest environment has `jsdom` configured. Recharts components require mocking `ResizeObserver` in tests since jsdom does not implement it.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Treemap renders with 100 stock cells | unit | `npm test -- --watchAll=false --testPathPattern="SentimentHeatmap"` | No — Wave 0 |
| UI-02 | Sector grouping: 9 sectors + OTHER shown | unit | `npm test -- --watchAll=false --testPathPattern="SentimentHeatmap"` | No — Wave 0 |
| UI-02 | `buildHeatmapData()` places EQIX+SPG in OTHER | unit | `npm test -- --watchAll=false --testPathPattern="heatmapUtils"` | No — Wave 0 |
| UI-03 | ComposedChart renders Area + Bar with dual axes | unit | `npm test -- --watchAll=false --testPathPattern="CompanyPage"` | No — Wave 0 |
| UI-04 | useInterval fires callback at configured interval | unit | `npm test -- --watchAll=false --testPathPattern="useInterval"` | No — Wave 0 |
| UI-04 | useInterval skips tick when visibilityState=hidden | unit | `npm test -- --watchAll=false --testPathPattern="useInterval"` | No — Wave 0 |
| UI-05 | "Updating..." text shown when isRefreshing=true | unit | `npm test -- --watchAll=false --testPathPattern="StockDataContext"` | No — Wave 0 |
| UI-06 | Skeleton shows when loading=true | unit | `npm test -- --watchAll=false --testPathPattern="SkeletonLoader"` | No — Wave 0 |
| UI-07 | Error state shows endpoint name + Retry button | unit | `npm test -- --watchAll=false --testPathPattern="StockDataContext"` | No — Wave 0 |
| UI-09 | interpolateSentimentColor returns correct hex | unit | `npm test -- --watchAll=false --testPathPattern="sentimentColor"` | No — Wave 0 |
| UI-10 | Pill badge renders green for positive, red for negative | unit | `npm test -- --watchAll=false --testPathPattern="PctBadge"` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `npm test -- --watchAll=false --testPathPattern="<affected component>"`
- **Per wave merge:** `npm test -- --watchAll=false`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/hooks/useInterval.test.js` — covers UI-04 (visibility API mocking requires `Object.defineProperty(document, 'visibilityState', ...)`)
- [ ] `src/utils/sentimentColor.test.js` — covers `interpolateSentimentColor()` for all 5 breakpoints + midpoints
- [ ] `src/utils/heatmapUtils.test.js` — covers `buildHeatmapData()`, OTHER grouping (UI-02), EQIX/SPG placement
- [ ] `src/context/StockDataContext.test.js` — covers context shape after refactor, loading/error/refresh states
- [ ] `src/components/SentimentHeatmap/SentimentHeatmap.test.js` — covers UI-01/UI-02 (requires ResizeObserver mock)
- [ ] `src/components/CompanyPage/CompanyPage.test.js` — update existing for dual-axis chart (UI-03)
- [ ] `src/__mocks__/ResizeObserverMock.js` — required by all Recharts component tests in jsdom
- [ ] `src/setupTests.js` — add `global.ResizeObserver = require('./__mocks__/ResizeObserverMock').default`

---

## Sources

### Primary (HIGH confidence)
- Recharts GitHub `recharts/recharts` 2.x branch, `src/chart/Treemap.tsx` — `content` render prop `nodeProps` structure (confirmed `x, y, width, height, depth, name, value, root` are passed)
- Recharts GitHub `recharts/recharts` 2.x branch, `demo/component/Treemap.tsx` — `DemoTreemapItem` pattern for custom content
- MUI v5 official docs `mui.com/material-ui/api/skeleton/` — `sx={{ bgcolor }}` and `animation="wave"` confirmed
- MUI v5 official docs `mui.com/material-ui/api/linear-progress/` — `sx` positioning confirmed
- Recharts official docs `recharts.github.io/en-US/api/YAxis` — `yAxisId` and `orientation` props confirmed
- `backend/main.py` lines 521–811 — all four endpoints inspected; response shapes confirmed; auth mechanism confirmed
- `backend/tickers.py` — `SECTOR_TICKERS`, `TICKER_DATA` fully read; sector counts verified

### Secondary (MEDIUM confidence)
- overreacted.io "Making setInterval Declarative with React Hooks" (Dan Abramov) — `useInterval` pattern; canonical reference widely adopted
- GitHub issue recharts #1281 — `isAnimationActive={false}` unreliable on Treemap data update; workaround via stable reference confirmed

### Tertiary (LOW confidence)
- WebSearch results on `useInterval` + visibility API — pattern described consistently across multiple sources; implementation verified against Dan Abramov's canonical article

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in `package.json`
- Architecture patterns: HIGH — verified against Recharts GitHub source and MUI official docs
- Pitfalls: HIGH — pitfalls 1-5 verified against source code reading; pitfalls 6-7 are MEDIUM (pattern extrapolation from known React behaviors)
- Open question 2 (sentiment scores for heatmap): LOW — requires further inspection of `main.py` sentiment pipeline to confirm whether per-ticker scores are accessible in a single endpoint

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (30 days — Recharts and MUI are stable; no fast-moving dependencies)
