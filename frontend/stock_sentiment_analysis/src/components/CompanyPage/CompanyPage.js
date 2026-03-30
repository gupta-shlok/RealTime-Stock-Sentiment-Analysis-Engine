import React, { useContext, useEffect, useState, useRef, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StockDataContext } from '../../context/StockDataContext';
import { getNewsData, getSentimentTrends, getStockNarrative } from '../../apis/api';
import NewsItem from '../NewsItem/NewsItem';
import { ComposedChart, Area, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Skeleton, Button } from '@mui/material';
import { CHART_THEME } from '../../utils/chartTheme';
import './CompanyPage.css';

const CompanyPage = () => {
    const { ticker } = useParams();
    const { stocks } = useContext(StockDataContext);
    const stock = stocks.find(s => s.name === ticker);

    const [companyNews, setCompanyNews] = useState([]);
    const [loadingNews, setLoadingNews] = useState(true);

    const [sentimentTrends, setSentimentTrends] = useState([]);
    const [trendsLoading, setTrendsLoading] = useState(true);
    const [trendsError, setTrendsError] = useState(null);

    const [narrative, setNarrative] = useState(null);
    const [narrativeLoading, setNarrativeLoading] = useState(true);
    const [narrativeError, setNarrativeError] = useState(null);
    const narrativePollRef = React.useRef(null);
    const narrativePollCountRef = React.useRef(0);

    // Prepare chart data from stock.history
    const chartData = stock ? (stock.history || []) : [];

    // Merge price history with sentiment trends by date
    const chartDataWithSentiment = useMemo(() => {
        const trendMap = {};
        sentimentTrends.forEach(t => { trendMap[t.date] = t.score; });
        return chartData.slice(-7).map(d => ({
            ...d,
            sentiment: trendMap[d.Date] ?? null,
        }));
    }, [chartData, sentimentTrends]);

    useEffect(() => {
        if (ticker) {
            setLoadingNews(true);
            getNewsData(ticker)
                .then(data => {
                    setCompanyNews(data);
                    setLoadingNews(false);
                })
                .catch(err => {
                    console.error("Error fetching company news:", err);
                    setLoadingNews(false);
                });
        }
    }, [ticker]);

    useEffect(() => {
        if (!ticker) return;
        setTrendsLoading(true);
        setTrendsError(null);
        getSentimentTrends(ticker, '7d')
            .then(data => {
                setSentimentTrends(data.data || []);
                setTrendsLoading(false);
            })
            .catch(() => {
                setTrendsError(`Could not load sentiment trends for ${ticker}.`);
                setTrendsLoading(false);
            });
    }, [ticker]);

    useEffect(() => {
        if (!ticker) return;
        setNarrativeLoading(true);
        setNarrativeError(null);
        narrativePollCountRef.current = 0;

        const pollNarrative = () => {
            getStockNarrative(ticker)
                .then(data => {
                    if (data.status === 'complete') {
                        setNarrative(data);
                        setNarrativeLoading(false);
                        clearInterval(narrativePollRef.current);
                    } else if (data.status === 'pending') {
                        narrativePollCountRef.current += 1;
                        if (narrativePollCountRef.current >= 30) {
                            // Timeout after 5 minutes (30 × 10s)
                            setNarrativeError(`Could not load narrative for ${ticker}.`);
                            setNarrativeLoading(false);
                            clearInterval(narrativePollRef.current);
                        }
                        // else keep polling
                    }
                })
                .catch(() => {
                    setNarrativeError(`Could not load narrative for ${ticker}.`);
                    setNarrativeLoading(false);
                    clearInterval(narrativePollRef.current);
                });
        };

        pollNarrative(); // immediate first call
        narrativePollRef.current = setInterval(pollNarrative, 10000);

        return () => clearInterval(narrativePollRef.current);
    }, [ticker]);

    if (!stock) {
        return (
            <div className="company-page-error">
                <h2>Stock {ticker} not found in our database.</h2>
                <Link to="/" className="back-btn">Back to Dashboard</Link>
            </div>
        );
    }

    return (
        <div className="company-page glass-panel">
            <div className="company-header">
                <Link to="/" className="back-link">← Back to Dashboard</Link>
                <div className="company-title-row">
                    <h1>{stock.name} <span className="ticker-label">Ticker</span></h1>
                    <div className="company-price-box">
                        <span className="current-price">${stock.current_close?.toFixed(2)}</span>
                        <span className={`pct-badge ${stock.percent_change >= 0 ? 'pct-badge--up' : 'pct-badge--down'}`}>
                            {stock.percent_change >= 0 ? '+' : ''}{stock.percent_change?.toFixed(2)}%
                        </span>
                    </div>
                </div>
            </div>

            <div className="company-content">
                <div className="chart-section glass-card">
                    <h3>Performance + Sentiment (7 Days)</h3>
                    <div className="chart-wrapper">
                        {trendsLoading ? (
                            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: '16px', backgroundColor: 'var(--bg-elevated)' }} />
                        ) : trendsError ? (
                            <div className="chart-error">
                                <p>{trendsError}</p>
                                <Button variant="outlined" size="small" onClick={() => {
                                    setTrendsLoading(true);
                                    setTrendsError(null);
                                    getSentimentTrends(ticker, '7d')
                                        .then(d => { setSentimentTrends(d.data || []); setTrendsLoading(false); })
                                        .catch(() => { setTrendsError(`Could not load sentiment trends for ${ticker}.`); setTrendsLoading(false); });
                                }} sx={{ color: 'var(--text-secondary)', borderColor: 'var(--text-disabled)', mt: 1 }}>
                                    Retry
                                </Button>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={300}>
                                <ComposedChart data={chartDataWithSentiment}>
                                    <defs>
                                        <linearGradient id="colorPriceFill" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/>
                                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridColor} />
                                    <XAxis dataKey="Date" stroke={CHART_THEME.axisColor} fontSize={11} tick={{ fill: CHART_THEME.axisColor }} />
                                    <YAxis yAxisId="left" orientation="left" stroke={CHART_THEME.priceStroke} fontSize={11}
                                        tick={{ fill: CHART_THEME.axisColor }} domain={['auto', 'auto']}
                                        tickFormatter={v => `$${v.toFixed(0)}`} />
                                    <YAxis yAxisId="right" orientation="right" stroke={CHART_THEME.axisColor} fontSize={11}
                                        tick={{ fill: CHART_THEME.axisColor }} domain={[-1, 1]}
                                        tickFormatter={v => v.toFixed(1)} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: CHART_THEME.tooltipBg, border: 'none', borderRadius: '8px', color: '#fff' }}
                                    />
                                    <Area yAxisId="left" type="monotone" dataKey="Close"
                                        stroke="#3b82f6" strokeWidth={2}
                                        fill="url(#colorPriceFill)"
                                        isAnimationActive={false}
                                        dot={false} />
                                    <Bar yAxisId="right" dataKey="sentiment" isAnimationActive={false}>
                                        {chartDataWithSentiment.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={(entry.sentiment ?? 0) >= 0 ? '#4ade80' : '#f87171'} />
                                        ))}
                                    </Bar>
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>

                <div className="metrics-grid">
                    <div className="metric-card glass-card">
                        <span>Previous Close</span>
                        <strong>${stock.previous_close?.toFixed(2)}</strong>
                    </div>
                    <div className="metric-card glass-card">
                        <span>Year High</span>
                        <strong>${Math.max(...chartData.map(d => d.High)).toFixed(2)}</strong>
                    </div>
                    <div className="metric-card glass-card">
                        <span>Year Low</span>
                        <strong>${Math.min(...chartData.map(d => d.Low)).toFixed(2)}</strong>
                    </div>
                </div>

                <div className="narrative-section glass-card">
                    <h3 className="section-label">AI Market Narrative</h3>
                    {narrativeLoading ? (
                        <>
                            <Skeleton variant="rectangular" height={96} sx={{ borderRadius: '8px', backgroundColor: 'var(--bg-elevated)', mb: 1 }} />
                            <p className="narrative-pending-caption">Generating narrative...</p>
                        </>
                    ) : narrativeError ? (
                        <div className="narrative-error">
                            <p>{narrativeError}</p>
                            <Button variant="outlined" size="small" onClick={() => {
                                setNarrativeError(null);
                                setNarrativeLoading(true);
                                narrativePollCountRef.current = 0;
                                const poll = () => {
                                    getStockNarrative(ticker)
                                        .then(data => {
                                            if (data.status === 'complete') {
                                                setNarrative(data); setNarrativeLoading(false);
                                                clearInterval(narrativePollRef.current);
                                            } else { narrativePollCountRef.current += 1; if (narrativePollCountRef.current >= 30) { setNarrativeError(`Could not load narrative for ${ticker}.`); setNarrativeLoading(false); clearInterval(narrativePollRef.current); } }
                                        })
                                        .catch(() => { setNarrativeError(`Could not load narrative for ${ticker}.`); setNarrativeLoading(false); clearInterval(narrativePollRef.current); });
                                };
                                poll();
                                narrativePollRef.current = setInterval(poll, 10000);
                            }} sx={{ color: 'var(--text-secondary)', borderColor: 'var(--text-disabled)', mt: 1 }}>
                                Retry
                            </Button>
                        </div>
                    ) : narrative ? (
                        <>
                            <p className="narrative-text">{narrative.narrative}</p>
                            <p className="narrative-staleness">
                                Generated {Math.floor((Date.now() - new Date(narrative.generated_at)) / 60000)} min ago
                            </p>
                        </>
                    ) : null}
                </div>

                <div className="company-news-section">
                    <h2>Latest {stock.name} News</h2>
                    {loadingNews ? (
                        <div className="loading-spinner">Fetching latest headlines...</div>
                    ) : (
                        <div className="company-news-grid">
                            {companyNews.map((news, idx) => (
                                <NewsItem key={idx} news={news} />
                            ))}
                            {companyNews.length === 0 && <p>No specific news found for this ticker.</p>}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CompanyPage;
