import React, { useContext, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StockDataContext } from '../../context/StockDataContext';
import { getNewsData } from '../../apis/api';
import NewsItem from '../NewsItem/NewsItem';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import './CompanyPage.css';

const CompanyPage = () => {
    const { ticker } = useParams();
    const stockData = useContext(StockDataContext);
    const [companyNews, setCompanyNews] = useState([]);
    const [loadingNews, setLoadingNews] = useState(true);

    const stock = stockData.find(s => s.name === ticker);

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

    if (!stock) {
        return (
            <div className="company-page-error">
                <h2>Stock {ticker} not found in our database.</h2>
                <Link to="/" className="back-btn">Back to Dashboard</Link>
            </div>
        );
    }

    // Prepare chart data from stock.history
    const chartData = stock.history || [];

    return (
        <div className="company-page glass-panel">
            <div className="company-header">
                <Link to="/" className="back-link">← Back to Dashboard</Link>
                <div className="company-title-row">
                    <h1>{stock.name} <span className="ticker-label">Ticker</span></h1>
                    <div className="company-price-box">
                        <span className="current-price">${stock.current_close?.toFixed(2)}</span>
                        <span className={`price-change ${stock.percent_change >= 0 ? 'up' : 'down'}`}>
                            {stock.percent_change >= 0 ? '+' : ''}{stock.percent_change?.toFixed(2)}%
                        </span>
                    </div>
                </div>
            </div>

            <div className="company-content">
                <div className="chart-section glass-card">
                    <h3>Performance History (1 Year)</h3>
                    <div className="chart-wrapper">
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="Month" stroke="#94a3b8" fontSize={12} />
                                <YAxis hide domain={['auto', 'auto']} />
                                <Tooltip 
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
                                    itemStyle={{ color: '#3b82f6' }}
                                />
                                <Area type="monotone" dataKey="Close" stroke="#3b82f6" fillOpacity={1} fill="url(#colorClose)" strokeWidth={3} />
                            </AreaChart>
                        </ResponsiveContainer>
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
