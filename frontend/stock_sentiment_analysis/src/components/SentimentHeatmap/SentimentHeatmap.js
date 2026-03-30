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

// 5-stop diverging palette: -1.0=#dc2626, -0.4=#f87171, 0.0=#475569, +0.4=#4ade80, +1.0=#16a34a
function getSentimentColor(score) {
    if (score === null || score === undefined) return '#475569';
    const s = Math.max(-1, Math.min(1, score));
    if (s >= 0.4) return lerpColor('#4ade80', '#16a34a', (s - 0.4) / 0.6);
    if (s >= 0)   return lerpColor('#475569', '#4ade80', s / 0.4);
    if (s >= -0.4) return lerpColor('#f87171', '#475569', (s + 0.4) / 0.4);
    return lerpColor('#dc2626', '#f87171', (s + 1) / 0.6);
}

// SECTORS_WITH_FEW_STOCKS: Real Estate (EQIX, SPG) + Materials (LIN) have stock_count < 3
const FEW_STOCK_TICKERS = new Set(['EQIX', 'SPG', 'LIN']);

function buildTreemapData(stocks) {
    const sectorMap = {};
    const otherChildren = [];

    stocks.forEach(stock => {
        const sentiment = stock.sentiment_score ?? null;
        const marketCap = stock.market_cap ?? 1;
        const node = { name: stock.name, value: marketCap, sentiment, displayName: stock.name, current_close: stock.current_close, percent_change: stock.percent_change };

        if (FEW_STOCK_TICKERS.has(stock.name)) {
            otherChildren.push(node);
        } else {
            const sector = stock.sector || 'Unknown';
            if (!sectorMap[sector]) sectorMap[sector] = [];
            sectorMap[sector].push(node);
        }
    });

    const result = Object.entries(sectorMap).map(([sector, children]) => ({
        name: sector,
        children,
    }));

    if (otherChildren.length > 0) {
        result.push({ name: 'OTHER', children: otherChildren });
    }

    return result;
}

const CustomTreemapContent = ({ x, y, width, height, name, sentiment, depth, onCellClick }) => {
    if (depth === 0) {
        // Sector group node — render semi-transparent label overlay
        const isOther = name === 'OTHER';
        return (
            <g>
                <text
                    x={x + 6} y={y + 16}
                    fontSize={12} fontWeight={700}
                    letterSpacing="0.08em"
                    style={{ textTransform: 'uppercase', pointerEvents: 'none', fill: isOther ? 'var(--text-disabled)' : 'var(--text-secondary)' }}
                >
                    {name}
                </text>
            </g>
        );
    }

    const fill = getSentimentColor(sentiment);
    const showTicker = width > 40;
    return (
        <g style={{ cursor: 'pointer' }} onClick={() => onCellClick(name)}>
            <rect
                x={x + 1} y={y + 1}
                width={Math.max(0, width - 2)} height={Math.max(0, height - 2)}
                fill={fill}
                stroke="rgba(0,0,0,0.25)"
                strokeWidth={1}
                rx={2}
            />
            {showTicker && (
                <text
                    x={x + width / 2} y={y + height / 2}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={Math.min(11, width / 5)}
                    fontFamily="'JetBrains Mono', monospace"
                    fontWeight="700"
                    fill="rgba(255,255,255,0.88)"
                    style={{ pointerEvents: 'none' }}
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
            <ResponsiveContainer width="100%" height={480}>
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
                            if (!d || d.children) return null; // Skip sector nodes
                            const pct = d.percent_change;
                            const sentimentStr = d.sentiment !== null && d.sentiment !== undefined
                                ? (d.sentiment >= 0 ? '+' : '') + d.sentiment.toFixed(2)
                                : 'N/A';
                            return (
                                <div className="heatmap-tooltip">
                                    <div className="tooltip-ticker">{d.name}</div>
                                    <div className="tooltip-price">${d.current_close?.toFixed(2)}</div>
                                    <div className="tooltip-sentiment">Sentiment: {sentimentStr}</div>
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
