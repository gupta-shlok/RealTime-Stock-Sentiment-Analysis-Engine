import React, { useContext, useMemo, useRef } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { StockDataContext } from '../../context/StockDataContext';
import { useNavigate } from 'react-router-dom';
import './SentimentHeatmap.css';

// Interpolate between two hex colors by fraction t in [0, 1]
function lerpColor(hex1, hex2, t) {
    const r1 = parseInt(hex1.slice(1, 3), 16);
    const g1 = parseInt(hex1.slice(3, 5), 16);
    const b1 = parseInt(hex1.slice(5, 7), 16);
    const r2 = parseInt(hex2.slice(1, 3), 16);
    const g2 = parseInt(hex2.slice(3, 5), 16);
    const b2 = parseInt(hex2.slice(5, 7), 16);
    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);
    return `rgb(${r},${g},${b})`;
}

// 5-stop diverging palette: -1.0=#dc2626, -0.4=#f87171, 0.0=#334f6e, +0.4=#4ade80, +1.0=#16a34a
// Neutral is a distinct steel blue — clearly different from both the dark bg-surface (#1e293b) and sentiment colors
function getSentimentColor(score) {
    if (score === null || score === undefined) return '#334f6e';
    const s = Math.max(-1, Math.min(1, score));
    if (s >= 0.4) return lerpColor('#4ade80', '#16a34a', (s - 0.4) / 0.6);
    if (s >= 0)   return lerpColor('#334f6e', '#4ade80', s / 0.4);
    if (s >= -0.4) return lerpColor('#f87171', '#334f6e', (s + 0.4) / 0.4);
    return lerpColor('#dc2626', '#f87171', (s + 1) / 0.6);
}

function buildTreemapData(stocks) {
    return stocks.map(stock => ({
        name: stock.name,
        value: Math.sqrt(stock.market_cap ?? 1),
        sentiment: stock.sentiment_score ?? null,
        sector: stock.sector || 'Unknown',
        current_close: stock.current_close,
        percent_change: stock.percent_change,
    }));
}

const CustomTreemapContent = ({ x, y, width, height, name, sentiment, onCellClick }) => {
    const fill = getSentimentColor(sentiment);
    const showTicker = width > 28 && height > 16;
    return (
        <g style={{ cursor: 'pointer' }} onClick={() => onCellClick(name)}>
            <rect
                x={x + 1} y={y + 1}
                width={Math.max(0, width - 2)} height={Math.max(0, height - 2)}
                fill={fill}
                stroke="rgba(0,0,0,0.35)"
                strokeWidth={1}
                rx={4}
            />
            {showTicker && (
                <text
                    x={x + width / 2} y={y + height / 2}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={Math.min(11, Math.max(7, width / 5))}
                    fontFamily="'JetBrains Mono', monospace"
                    fontWeight="700"
                    fill="rgba(255,255,255,0.95)"
                    stroke="rgba(0,0,0,0.5)"
                    strokeWidth={2}
                    style={{ pointerEvents: 'none', paintOrder: 'stroke fill' }}
                >
                    {name}
                </text>
            )}
        </g>
    );
};

const SentimentHeatmap = () => {
    const { stocks, loading, error } = useContext(StockDataContext);
    const treeDataRef = useRef(null);
    const navigate = useNavigate();

    const handleCellClick = (ticker) => {
        navigate(`/stock/${ticker}`);
    };

    // Build treemap data; mutate in-place on updates to prevent re-animation (per D-10)
    // useMemo returns the SAME array reference if it already exists — we update values in-place
    const treeData = useMemo(() => {
        const newData = buildTreemapData(stocks);
        if (!treeDataRef.current) {
            treeDataRef.current = newData;
            return treeDataRef.current;
        }
        // Mutate existing reference in-place to prevent Recharts re-animation
        // Replace array contents without creating new array reference
        treeDataRef.current.splice(0, treeDataRef.current.length, ...newData);
        return treeDataRef.current;
    }, [stocks]);

    if (loading) {
        return (
            <div className="heatmap-skeleton" style={{ height: 400, width: '100%', borderRadius: 16, background: 'var(--bg-elevated)' }} />
        );
    }

    if (error) {
        return (
            <div className="heatmap-error">
                <p>Could not load stock data. Check your connection and try again.</p>
            </div>
        );
    }

    if (!stocks.length) {
        return (
            <div className="heatmap-empty">
                <p className="section-label">No sentiment data available</p>
                <p>Sentiment scores have not been computed yet. Data refreshes every 10 minutes.</p>
            </div>
        );
    }

    return (
        <div className="sentiment-heatmap surface-card">
            <h2 className="section-label">Market Sentiment</h2>
            <ResponsiveContainer width="100%" height={600}>
                <Treemap
                    data={treeData}
                    dataKey="value"
                    aspectRatio={4 / 3}
                    isAnimationActive={false}
                    content={<CustomTreemapContent onCellClick={handleCellClick} />}
                >
                    <Tooltip
                        content={({ active, payload }) => {
                            if (!active || !payload || !payload.length) return null;
                            const d = payload[0].payload;
                            if (!d || !d.name) return null;
                            const pct = d.percent_change;
                            const sentimentStr = d.sentiment !== null && d.sentiment !== undefined
                                ? (d.sentiment >= 0 ? '+' : '') + d.sentiment.toFixed(2)
                                : 'N/A';
                            return (
                                <div className="heatmap-tooltip">
                                    <div className="tooltip-ticker">{d.name}</div>
                                    {d.sector && <div className="tooltip-sector">{d.sector}</div>}
                                    <div className="tooltip-price">${d.current_close?.toFixed(2)}</div>
                                    <div className="tooltip-sentiment">
                                        Sentiment: <span style={{ color: d.sentiment >= 0 ? '#4ade80' : '#f87171', fontWeight: 700 }}>{sentimentStr}</span>
                                    </div>
                                    {pct !== undefined && (
                                        <span className={`pct-badge ${pct >= 0 ? 'pct-badge--up' : 'pct-badge--down'}`}>
                                            {pct >= 0 ? '+' : ''}{pct?.toFixed(2)}%
                                        </span>
                                    )}
                                </div>
                            );
                        }}
                    />
                </Treemap>
            </ResponsiveContainer>
        </div>
    );
};

export default SentimentHeatmap;
