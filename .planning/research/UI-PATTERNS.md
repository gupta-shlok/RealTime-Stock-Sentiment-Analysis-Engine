# UI Patterns Research: Stock Sentiment Dashboard

**Project:** RealTime Stock Sentiment Analysis Engine
**Stack context:** React 18, Recharts 2.x, MUI v5, dark theme (`#0f172a` bg)
**Researched:** 2026-03-26
**Overall confidence:** MEDIUM-HIGH (verified against official docs and multiple sources)

---

## 1. Sentiment Heatmap Patterns

### Recommended approach: Recharts `<Treemap>` with custom content

Recharts ships a `<Treemap>` component natively. For 100 US equities it is the correct primitive. A grid layout (uniform cells) is simpler but wastes the visual bandwidth that size encoding provides. A bubble chart introduces overlap at this scale. The treemap is what Finviz, TradingView, and Bloomberg all use for market-wide snapshots for good reason.

**Data shape Recharts Treemap expects:**

```js
const data = [
  {
    name: 'AAPL',
    size: 3000,           // drives cell area — use market cap or float-adjusted market cap
    sentimentScore: 0.72, // -1.0 to 1.0; drives cell color
    percentChange: 1.4,   // shown in label
  },
  // ...99 more
];
```

Key props on `<Treemap>`:
- `dataKey="size"` — which field controls cell area
- `content={<CustomCell />}` — render prop for full control over fill and label
- `nameKey="name"` — ticker label
- `isAnimationActive={false}` — disable for dashboards; re-animation on every poll is distracting

**`customContent` pattern for color-by-sentiment:**

```jsx
const SentimentCell = ({ x, y, width, height, name, sentimentScore, percentChange }) => {
  const fill = getSentimentColor(sentimentScore); // see color scale below

  if (width < 30 || height < 20) return null; // skip labels on tiny cells

  return (
    <g>
      <rect
        x={x} y={y}
        width={width} height={height}
        fill={fill}
        stroke="rgba(15, 23, 42, 0.6)" // --bg-primary at 60% opacity
        strokeWidth={2}
        rx={3}
      />
      <text x={x + width / 2} y={y + height / 2 - 6}
        textAnchor="middle" fill="#f8fafc"
        fontSize={Math.min(14, width / 4)}
        fontWeight={600} fontFamily="Inter, sans-serif">
        {name}
      </text>
      <text x={x + width / 2} y={y + height / 2 + 10}
        textAnchor="middle" fill="rgba(248,250,252,0.75)"
        fontSize={Math.min(11, width / 5)}>
        {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(2)}%
      </text>
    </g>
  );
};
```

### Color scale for sentiment

Use a **5-stop diverging scale** centered on neutral. Sentiment scores typically run -1.0 to +1.0; map them as below.

**Primary palette (dark background optimized):**

| Score range | Meaning | Hex | CSS variable suggestion |
|-------------|---------|-----|------------------------|
| +0.5 to +1.0 | Strong positive | `#16a34a` | `--sentiment-strong-pos` |
| +0.1 to +0.5 | Mild positive | `#4ade80` | `--sentiment-mild-pos` |
| -0.1 to +0.1 | Neutral | `#475569` | `--sentiment-neutral` |
| -0.5 to -0.1 | Mild negative | `#f87171` | `--sentiment-mild-neg` |
| -1.0 to -0.5 | Strong negative | `#dc2626` | `--sentiment-strong-neg` |

These greens and reds are distinct enough from the `#3b82f6` accent the project already uses and have sufficient contrast on dark backgrounds. The neutral slate (`#475569`) reads clearly as "neither."

**Accessibility caveat (confidence: HIGH):** Pure red/green fails for ~8% of male users with red-green color blindness. Pair hue with lightness shift — the strong-positive green is lighter than the mild-positive green, and the strong-negative red is darker than the mild-negative red. This means even in greyscale the intensity difference communicates magnitude. A secondary label (score number) inside larger cells further removes hue-only dependence.

**Color interpolation function:**

```js
function getSentimentColor(score) {
  // score is -1.0 to 1.0
  if (score >= 0.5)  return '#16a34a';
  if (score >= 0.1)  return '#4ade80';
  if (score >= -0.1) return '#475569';
  if (score >= -0.5) return '#f87171';
  return '#dc2626';
}
```

For smoother gradients between stops, interpolate in HSL space rather than RGB. A utility like `chroma-js` handles this in two lines, but for five discrete stops the function above is sufficient and has zero dependency cost.

### Treemap sizing strategies

- **Market cap sizing (recommended):** Larger companies occupy proportionally more area. This mirrors Finviz and TradingView conventions and communicates index concentration at a glance.
- **Equal sizing:** Every cell is the same area. Easier to implement (pass `size: 1` for all), better for comparing equal-weight sentiment across all 100 stocks. Choose this if market cap data is unavailable.
- **Volume sizing:** Size by today's trading volume. Surfaces which stocks are getting attention today rather than which are largest.

**Recommendation for this project:** Use equal sizing initially (set `size: 1`). Market cap data requires a separate API. Equal sizing lets the heatmap ship and still communicate sentiment effectively. Add market cap sizing as a Phase 2 enhancement once the data pipeline supports it.

---

## 2. Chart Overlay Patterns (Price + Sentiment)

### The right Recharts primitive: `<ComposedChart>`

`ComposedChart` is the only Recharts chart type that lets you combine `<Area>`, `<Bar>`, and `<Line>` in a single coordinate system. It replaces `<LineChart>` or `<AreaChart>` when you need overlays.

### Dual Y-axis pattern (confidence: HIGH — official Recharts docs)

Price and sentiment score live on incompatible scales (e.g., $150-$200 vs -1.0 to 1.0). You need two `<YAxis>` components, each with a `yAxisId`, and each data series references its axis by that id.

```jsx
import {
  ComposedChart, Area, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

// Data shape: each point has a date, close price, and sentiment score
const data = [
  { month: 'Jan', close: 182.5, sentiment: 0.42 },
  { month: 'Feb', close: 179.1, sentiment: -0.15 },
  // ...
];

<ResponsiveContainer width="100%" height={320}>
  <ComposedChart data={data} margin={{ top: 8, right: 40, left: 0, bottom: 0 }}>
    <defs>
      <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25} />
        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
      </linearGradient>
    </defs>

    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
    <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />

    {/* Left axis: price */}
    <YAxis
      yAxisId="price"
      orientation="left"
      stroke="#94a3b8"
      fontSize={11}
      tickFormatter={(v) => `$${v}`}
      domain={['auto', 'auto']}
    />

    {/* Right axis: sentiment — fixed domain keeps 0 as center */}
    <YAxis
      yAxisId="sentiment"
      orientation="right"
      stroke="#94a3b8"
      fontSize={11}
      domain={[-1, 1]}
      tickCount={5}
      tickFormatter={(v) => v.toFixed(1)}
    />

    <Tooltip content={<DualAxisTooltip />} />

    {/* Price area on left axis */}
    <Area
      yAxisId="price"
      type="monotone"
      dataKey="close"
      stroke="#3b82f6"
      strokeWidth={2}
      fill="url(#priceGradient)"
    />

    {/* Sentiment bars on right axis */}
    <Bar
      yAxisId="sentiment"
      dataKey="sentiment"
      maxBarSize={8}
      fill="#4ade80"
      radius={[2, 2, 0, 0]}
      // Custom cell fill per value — positive=green, negative=red
      label={false}
    >
      {data.map((entry, index) => (
        <Cell
          key={index}
          fill={entry.sentiment >= 0 ? '#4ade80' : '#f87171'}
          fillOpacity={Math.abs(entry.sentiment) * 0.8 + 0.2}
        />
      ))}
    </Bar>
  </ComposedChart>
</ResponsiveContainer>
```

Import `Cell` from `recharts` for the per-bar coloring.

### Custom tooltip for dual axes

The default Recharts tooltip does not know which axis a value belongs to. Write a custom `content` component:

```jsx
const DualAxisTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;

  const priceEntry = payload.find(p => p.dataKey === 'close');
  const sentimentEntry = payload.find(p => p.dataKey === 'sentiment');

  return (
    <div style={{
      background: '#1e293b',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 12,
      color: '#f8fafc',
      lineHeight: 1.8,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      {priceEntry && (
        <div style={{ color: '#3b82f6' }}>
          Price: ${priceEntry.value?.toFixed(2)}
        </div>
      )}
      {sentimentEntry && (
        <div style={{ color: sentimentEntry.value >= 0 ? '#4ade80' : '#f87171' }}>
          Sentiment: {sentimentEntry.value?.toFixed(3)}
        </div>
      )}
    </div>
  );
};
```

### Alternative: single normalized axis

If dual-axis visual complexity is a concern, normalize both series to a 0–100 scale before rendering and use a single `<YAxis>`. This is simpler but loses the dollar-value annotation on the price axis. For a portfolio project the dual-axis version reads as more sophisticated — keep it.

### Overlay vs. separate panels

Bloomberg and TradingView typically put sentiment in a **separate sub-panel** below the price chart (like RSI or MACD sub-charts). This keeps each axis unambiguous. In Recharts the cleanest implementation is two stacked `<ResponsiveContainer>` charts sharing the same `data` array and an `XAxis` with `tick={false}` on the top chart to eliminate duplication. Dual-axis on one chart is valid for shorter time windows; separate panels work better when the user needs to read exact values from both metrics simultaneously.

---

## 3. Stock Dashboard UX Conventions

### Layout hierarchy that reads as professional

**Header row:** Ticker + current price + % change badge. The change badge needs a colored background pill, not just colored text — colored text on dark backgrounds is harder to scan rapidly.

```
[ AAPL   $182.50   +1.4% ]  ← pill for the badge
```

**Grid density:** Bloomberg runs extremely high data density; Finviz runs high; TradingView runs medium. For a React dashboard targeting general users, medium density is correct. A 3-4 column grid for metric cards with `gap: 1rem` and `padding: 1.25rem` inside cards is the established pattern.

**Information hierarchy (inverted pyramid):**
1. Top: primary insight (overall market sentiment indicator, top movers)
2. Middle: interactive charts and heatmap
3. Bottom: news feed and supporting detail

This is what the current `HomePage` layout should aim toward — the scrolling ticker is a top-row element, the heatmap belongs in the center.

### Typography that makes dashboards feel professional

The project already uses Inter, which is the correct choice. Inter was designed for screens and is used by Figma, Linear, and most modern fintech products.

**Type scale for financial dashboards:**

| Role | Size | Weight | Color |
|------|------|--------|-------|
| Section heading | 0.8125rem (13px) | 500 | `#94a3b8` (text-secondary), all-caps, `letter-spacing: 0.06em` |
| Primary metric | 1.75rem (28px) | 700 | `#f8fafc` |
| Secondary metric | 1rem (16px) | 600 | `#f8fafc` |
| Positive change | 0.875rem (14px) | 500 | `#4ade80` |
| Negative change | 0.875rem (14px) | 500 | `#f87171` |
| Muted label | 0.75rem (12px) | 400 | `#64748b` |
| Chart axis labels | 11px | 400 | `#94a3b8` |

The all-caps, letter-spaced section heading (`SENTIMENT HEATMAP`, `PRICE HISTORY`, `TOP MOVERS`) is a Bloomberg convention that reliably signals "this is a financial data product." It is the single typography change with the highest signal-to-effort ratio.

### Color conventions users expect

These are established financial UI conventions (confidence: HIGH — consistent across Bloomberg, Finviz, TradingView):

- Positive change: green. Never blue, never teal.
- Negative change: red. Never orange, never pink.
- Neutral/flat: grey or white.
- The accent color (`#3b82f6` in this project) belongs on interactive elements and chart lines, not on financial performance indicators.

**Color badge pattern for % change:**

```css
.change-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8125rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums; /* keeps column alignment stable */
}
.change-badge.positive { background: rgba(22, 163, 74, 0.15); color: #4ade80; }
.change-badge.negative { background: rgba(220, 38, 38, 0.15); color: #f87171; }
```

The low-opacity background tint (`15%`) prevents the badge from screaming while still providing a clear zone of color.

### Data density patterns

- Use `font-variant-numeric: tabular-nums` on all price and percentage columns. This prevents horizontal jitter as numbers update.
- Right-align numbers in list views. Left-align labels. This is the universal convention — Bloomberg does it, terminal interfaces do it, data tables do it.
- Monospace font for numbers is not required with tabular-nums Inter, but `font-family: 'JetBrains Mono', monospace` on just the price display adds a professional data-terminal aesthetic with minimal cost.
- Show 2 decimal places for prices above $10, 4 for penny stocks. Show 2 decimal places for % change.
- Never truncate a number with an ellipsis — either show all digits or round to fewer decimals.

### Chart visual conventions

- **No chart borders.** Let charts bleed to the edges of their card container.
- **Minimal grid lines.** Use `strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"` — barely visible.
- **Smooth curves** (`type="monotone"`) for price charts. Straight segments (`type="linear"`) for sentiment bars.
- **Reference lines** work well for 52-week high/low or a zero line on sentiment.
- **No chart titles inside the chart.** Put the title in the card header above the chart.

---

## 4. Auto-Refresh Patterns in React

### Pattern 1: `useInterval` custom hook (recommended for this project)

This project uses plain `axios` and `useEffect`, not TanStack Query. The correct low-dependency pattern is a `useInterval` hook modeled after Dan Abramov's canonical implementation.

```js
// hooks/useInterval.js
import { useEffect, useRef } from 'react';

export function useInterval(callback, delay) {
  const savedCallback = useRef(callback);

  // Keep the callback ref current without restarting the interval
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return; // pass null to pause
    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}
```

Usage in a data-fetching component:

```js
const POLL_INTERVAL_MS = 60_000; // 60 seconds — appropriate for EOD/daily data

const [lastUpdated, setLastUpdated] = useState(null);
const [isRefreshing, setIsRefreshing] = useState(false);

const fetchData = useCallback(async () => {
  setIsRefreshing(true);
  try {
    const data = await getStockData();
    setStockData(data);
    setLastUpdated(new Date());
  } catch (err) {
    console.error('Refresh failed', err);
  } finally {
    setIsRefreshing(false);
  }
}, []);

// Initial fetch on mount
useEffect(() => { fetchData(); }, [fetchData]);

// Polling
useInterval(fetchData, POLL_INTERVAL_MS);
```

### Pattern 2: TanStack Query v5 `refetchInterval` (recommended if adopting React Query)

If the project later adopts `@tanstack/react-query`, the polling is declarative:

```js
const { data, isFetching, dataUpdatedAt } = useQuery({
  queryKey: ['stock-data'],
  queryFn: getStockData,
  refetchInterval: 60_000,
  refetchIntervalInBackground: false, // pause when tab is not visible
  staleTime: 30_000,
});
```

`isFetching` is `true` during background refetches (but `isLoading` is `false`), which gives you a clean signal for the refresh indicator without blocking the UI.

### Last-updated indicator pattern

The "last updated" timestamp is a professional convention for financial dashboards — it communicates data freshness and builds trust. Keep it subtle: small, muted, positioned in the card header's top-right corner.

```jsx
const LastUpdated = ({ timestamp, isRefreshing }) => {
  if (!timestamp) return null;

  const formatted = timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <span style={{
      fontSize: '0.6875rem',       // 11px
      color: '#64748b',
      display: 'flex',
      alignItems: 'center',
      gap: 5,
      fontVariantNumeric: 'tabular-nums',
    }}>
      {isRefreshing
        ? <span style={{ color: '#3b82f6' }}>Updating...</span>
        : `Updated ${formatted}`
      }
    </span>
  );
};
```

Place this in the top-right of a section header:

```jsx
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
  <h2 className="section-label">MARKET HEATMAP</h2>
  <LastUpdated timestamp={lastUpdated} isRefreshing={isRefreshing} />
</div>
```

### Non-disruptive loading: key rule

**Never unmount the chart or heatmap during a background refresh.** Update state in-place so Recharts re-renders with new data without destroying the component. The current `NewsData.js` violates this — it replaces the entire component with "Fetching latest news..." text when loading. The correct pattern:

```js
// WRONG — replaces UI on refresh
if (loading) return <div>Fetching...</div>;

// RIGHT — show stale data with a subtle indicator
return (
  <div className="section">
    {isRefreshing && <LinearProgress sx={{ height: 2, mb: 1 }} />}
    <DataComponent data={data} />  {/* always rendered */}
  </div>
);
```

MUI `<LinearProgress />` with `height: 2px` at the top of a card section is the standard non-disruptive in-progress indicator for dashboards. It costs one line of JSX and communicates refresh without obscuring content.

### Polling interval guidance

| Data type | Recommended interval |
|-----------|---------------------|
| Live price (market hours) | 15–30 seconds |
| EOD prices / historical | 5–15 minutes |
| Sentiment scores (NLP pipeline output) | 5 minutes |
| News feed | 2–5 minutes |

If backend data is updated by a batch job (not a live feed), polling faster than the batch cadence is wasted requests. Set `POLL_INTERVAL_MS` to match the backend's actual update frequency.

### Page visibility optimization

Stop polling when the browser tab is not active — there is no user to see the update, and it wastes API calls:

```js
useEffect(() => {
  const handleVisibility = () => {
    if (document.visibilityState === 'visible') {
      fetchData(); // immediate refresh on tab return
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, [fetchData]);
```

Combined with `useInterval`, pass `document.visibilityState === 'hidden' ? null : POLL_INTERVAL_MS` as the delay to pause the interval automatically.

---

## 5. Skeleton Loader Patterns

### Why skeleton over spinner for financial dashboards

Spinners communicate "something is happening, wait." Skeletons communicate "here is where your data will appear." For dashboard grids where layout matters — cards in a grid, a chart area, a news list — skeleton loaders eliminate Cumulative Layout Shift (CLS) and reduce the subjective perception of wait time.

**Rule:** Use skeleton for components that have a known layout shape. Use spinner only for actions (form submit, search) where result size is unknown.

### MUI v5 Skeleton — essential props

```jsx
import Skeleton from '@mui/material/Skeleton';

// Four variants:
<Skeleton variant="text" />        // single text line, auto-height from font-size
<Skeleton variant="rectangular" /> // no border-radius
<Skeleton variant="rounded" />     // 4px border-radius — use this for cards
<Skeleton variant="circular" />    // perfect circle — avatars, icons
```

**Animation:** Use `animation="wave"` for financial dashboards. The left-to-right shimmer reads as "data streaming in." Pulse (`animation="pulse"`, the default) is softer but passive.

**Dark theme fix — critical:** MUI Skeleton on dark backgrounds is nearly invisible by default. Override `bgcolor`:

```jsx
<Skeleton
  variant="rounded"
  animation="wave"
  sx={{ bgcolor: 'rgba(255, 255, 255, 0.06)' }}  // matches the project's --glass-border
  width="100%"
  height={120}
/>
```

### Skeleton patterns for each component type

**Metric card (matches existing `.metric-card` layout):**

```jsx
const MetricCardSkeleton = () => (
  <div className="metric-card glass-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
    <Skeleton variant="text" animation="wave"
      sx={{ bgcolor: 'rgba(255,255,255,0.06)', fontSize: '0.75rem', width: '60%' }} />
    <Skeleton variant="text" animation="wave"
      sx={{ bgcolor: 'rgba(255,255,255,0.06)', fontSize: '1.5rem', width: '80%' }} />
  </div>
);
```

**Area/line chart placeholder (prevents layout jump for the CompanyPage chart section):**

```jsx
const ChartSkeleton = ({ height = 300 }) => (
  <Skeleton
    variant="rectangular"
    animation="wave"
    sx={{
      bgcolor: 'rgba(255,255,255,0.04)',
      borderRadius: '4px',
    }}
    width="100%"
    height={height}
  />
);
```

**Treemap/heatmap placeholder (covers the full heatmap area):**

```jsx
const HeatmapSkeleton = () => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gap: 4 }}>
    {Array.from({ length: 100 }).map((_, i) => (
      <Skeleton
        key={i}
        variant="rectangular"
        animation="wave"
        sx={{ bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 2 }}
        height={60}
      />
    ))}
  </div>
);
```

The 10x10 grid skeleton gives a strong visual cue for "heatmap loading" even though real treemap cells are variable-size.

**News item skeleton (matches `NewsItem` card shape):**

```jsx
const NewsItemSkeleton = () => (
  <div className="news-item glass-card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
    {/* Headline — 2 lines */}
    <Skeleton variant="text" animation="wave"
      sx={{ bgcolor: 'rgba(255,255,255,0.06)', fontSize: '1rem', width: '90%' }} />
    <Skeleton variant="text" animation="wave"
      sx={{ bgcolor: 'rgba(255,255,255,0.06)', fontSize: '1rem', width: '70%' }} />
    {/* Source + timestamp */}
    <Skeleton variant="text" animation="wave"
      sx={{ bgcolor: 'rgba(255,255,255,0.06)', fontSize: '0.75rem', width: '40%' }} />
  </div>
);
```

**Ticker bar skeleton (matches the scrolling `.stock-chart-container`):**

```jsx
const TickerSkeleton = () => (
  <div style={{ display: 'flex', gap: '1.5rem', padding: '1rem 0', overflow: 'hidden' }}>
    {Array.from({ length: 12 }).map((_, i) => (
      <Skeleton key={i} variant="rounded" animation="wave"
        sx={{ bgcolor: 'rgba(255,255,255,0.06)', flexShrink: 0 }}
        width={100} height={48} />
    ))}
  </div>
);
```

### Staggered skeleton reveal

For grid layouts (metric cards, heatmap cells), animate skeletons with a staggered delay to prevent a uniform flash that looks artificial:

```jsx
// Add animation-delay to each skeleton based on index
<Skeleton
  sx={{
    bgcolor: 'rgba(255,255,255,0.06)',
    animationDelay: `${index * 50}ms`,   // 50ms stagger per cell
  }}
  ...
/>
```

### Skeleton sizing rule

Match the skeleton height exactly to the loaded content height. If a `<MetricCard>` with real data is 96px tall, the skeleton must also be 96px tall. Measure rendered heights and hard-code them in skeleton props. This is the only way to prevent layout shift on data arrival.

---

## Sources

- [Recharts Treemap CustomContent example](https://recharts.github.io/en-US/examples/CustomContentTreemap/) — treemap customContent API
- [Recharts BiAxial Line Chart (GeeksforGeeks)](https://www.geeksforgeeks.org/reactjs/create-a-biaxial-line-chart-using-recharts-in-reactjs/) — yAxisId dual axis pattern (MEDIUM confidence)
- [Recharts GitHub demo Treemap.tsx](https://github.com/recharts/recharts/blob/2.x/demo/component/Treemap.tsx) — canonical data shape and content prop usage
- [Awesome React Charts Tips — Leanylabs](https://leanylabs.com/blog/awesome-react-charts-tips/) — gradient fills, ComposedChart overlays
- [MUI Skeleton component](https://mui.com/material-ui/react-skeleton/) — variant/animation API (HIGH confidence, official docs)
- [MUI Skeleton dark theme issue #19957](https://github.com/mui/material-ui/issues/19957) — bgcolor override for dark mode
- [Polling in React with useInterval — OpenReplay](https://blog.openreplay.com/polling-in-react-using-the-useinterval-custom-hook/) — useInterval implementation
- [TanStack Query auto-refetching example](https://tanstack.com/query/v5/docs/framework/react/examples/auto-refetching) — refetchInterval / isFetching pattern
- [Cloudscape loading and refreshing patterns](https://cloudscape.design/patterns/general/loading-and-refreshing/) — last-updated timestamps, non-disruptive refresh (HIGH confidence)
- [Fintech dashboard design — merge.rocks](https://merge.rocks/blog/fintech-dashboard-design-or-how-to-make-data-look-pretty) — layout hierarchy, chart selection, timestamp conventions
- [TradingView stock heatmap guide](https://spartantrading.com/technology/tradingview-stock-heatmap/) — cell sizing/color conventions (MEDIUM confidence)
- [Financial data visualization techniques 2025](https://chartswatcher.com/pages/blog/top-financial-data-visualization-techniques-for-2025) — treemap conventions
- [Bloomberg color accessibility](https://www.bloomberg.com/company/stories/designing-the-terminal-for-color-accessibility/) — colorblind-safe palette rationale (HIGH confidence)
- [Heatmap color best practices — BioTuring](https://bioturing.medium.com/dos-and-donts-for-a-heatmap-color-scale-75929663988b) — diverging palette guidance
