// components/NewsData.js
import React, { useState, useEffect } from 'react';
import NewsItem from '../NewsItem/NewsItem';
import TopCompanies from '../TopCompanies/TopCompanies';
import { Skeleton, Button } from '@mui/material';
import './NewsData.css';

const NewsData = () => {
    const [newsItems, setNewsItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadNews = () => {
        setLoading(true);
        setError(null);
        // Use dynamic import for static JSON to get loading/error pattern
        import('../../news.json')
            .then(module => {
                setNewsItems(module.default || []);
                setLoading(false);
            })
            .catch(() => {
                setError('Could not load news articles.');
                setLoading(false);
            });
    };

    useEffect(() => { loadNews(); }, []);

    if (loading) {
        return (
            <div className="news-section">
                <div className="large-news">
                    <Skeleton variant="rectangular" height={240}
                        sx={{ borderRadius: '12px', bgcolor: 'rgba(255,255,255,0.08)', mb: 2 }} />
                </div>
                <div className="small-news">
                    {[1, 2, 3].map(i => (
                        <Skeleton key={i} variant="rectangular" height={80}
                            sx={{ borderRadius: '8px', bgcolor: 'rgba(255,255,255,0.08)', mb: 1 }} />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="news-section news-error">
                <p style={{ color: '#94a3b8', marginBottom: 8 }}>{error}</p>
                <Button variant="outlined" size="small" onClick={loadNews}
                    sx={{ color: '#94a3b8', borderColor: '#475569' }}>
                    Retry
                </Button>
            </div>
        );
    }

    const largeNewsItem = newsItems[0];
    const smallNewsItems = newsItems.slice(1, 4);

    return (
        <div className="news-section">
            <h2 className="section-label">Latest News</h2>
            <div className="large-news">
                {largeNewsItem && <NewsItem news={largeNewsItem} />}
            </div>
            <div className="small-news">
                {smallNewsItems.map((news, index) => (
                    <NewsItem key={index} news={news} size="small" />
                ))}
            </div>
            <TopCompanies />
        </div>
    );
};

export default NewsData;
