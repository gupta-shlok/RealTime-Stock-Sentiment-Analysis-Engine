/**
 * chartTheme.js — Recharts color constants for StockSentimentSense
 *
 * Recharts SVG attributes (stroke, fill on XAxis/YAxis/CartesianGrid) do NOT
 * inherit CSS custom properties. These constants mirror the dark-theme token
 * values. They are intentionally hardcoded — SVG attribute values bypass the
 * CSS cascade and cannot use var() references.
 *
 * If theme-responsive chart axis colors are needed in a future phase, read
 * theme from StockDataContext and select the appropriate constant set.
 */
export const CHART_THEME = {
    axisColor: '#94a3b8',                // --text-secondary dark value
    gridColor: 'rgba(255,255,255,0.07)', // subtle grid line
    tooltipBg: '#1e293b',                // --bg-surface dark value (Recharts contentStyle)
    tooltipBorder: 'rgba(255,255,255,0.08)', // --border dark value
    priceStroke: '#3b82f6',              // --accent-blue (same both themes)
    priceFill: 'rgba(59,130,246,0.12)',  // price area fill
    sentimentPos: '#4ade80',             // --color-positive (same both themes)
    sentimentNeg: '#f87171',             // --color-negative (same both themes)
};
