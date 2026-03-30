// components/NewsData.js
import React, { useState, useEffect } from 'react';
import { CircularProgress, Button } from '@mui/material';
import { getNewsData } from '../../apis/api';
import './NewsData.css';

/**
 * Converts a Unix timestamp (seconds) to a relative time string like "2h ago".
 * Falls back to empty string if providerPublishTime is absent.
 */
function getRelativeTime(unixSeconds) {
    if (!unixSeconds) return '';
    const diffMs = Date.now() - unixSeconds * 1000;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    return `${diffDays}d ago`;
}

/**
 * Returns the thumbnail URL from a news item, or null if none.
 * Handles null/undefined thumbnail and empty resolutions array.
 */
function getThumbnailUrl(news) {
    const url = news.thumbnail?.resolutions?.[0]?.url;
    return url || null;
}

const NewsData = () => {
    const [newsItems, setNewsItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadNews = () => {
        setLoading(true);
        setError(null);
        getNewsData()
            .then(data => {
                setNewsItems(Array.isArray(data) ? data : []);
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
            <div className="news-section news-loading">
                <CircularProgress size={40} />
                <p style={{ marginTop: 12, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Loading news...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="news-section news-error">
                <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>{error}</p>
                <Button
                    variant="outlined"
                    size="small"
                    onClick={loadNews}
                    sx={{ color: 'var(--text-secondary)', borderColor: 'var(--text-disabled)' }}
                >
                    Retry
                </Button>
            </div>
        );
    }

    const heroItem = newsItems[0];
    const secondaryItems = newsItems.slice(1, 4);

    if (!heroItem) {
        return (
            <div className="news-section">
                <h2 className="section-label">Latest News</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No news articles available.</p>
            </div>
        );
    }

    return (
        <div className="news-section">
            <h2 className="section-label">Latest News</h2>

            {/* Hero card — full-width with thumbnail on left */}
            <a
                href={heroItem.link}
                target="_blank"
                rel="noopener noreferrer"
                className="news-hero-card"
            >
                <img
                    src={getThumbnailUrl(heroItem) || ''}
                    alt={heroItem.title}
                    onError={(e) => { e.target.style.display = 'none'; }}
                    style={getThumbnailUrl(heroItem) ? {} : { display: 'none' }}
                />
                <div className="news-card-text">
                    <span className="news-card-headline">{heroItem.title}</span>
                    <span className="news-card-meta">
                        {heroItem.publisher && <span>{heroItem.publisher}</span>}
                        {heroItem.publisher && heroItem.providerPublishTime && (
                            <span className="news-card-meta-dot">·</span>
                        )}
                        {heroItem.providerPublishTime && (
                            <span>{getRelativeTime(heroItem.providerPublishTime)}</span>
                        )}
                    </span>
                </div>
            </a>

            {/* Secondary cards — 3-column grid */}
            {secondaryItems.length > 0 && (
                <div className="news-secondary-row">
                    {secondaryItems.map((news, index) => {
                        const thumbUrl = getThumbnailUrl(news);
                        return (
                            <a
                                key={news.link || index}
                                href={news.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="news-secondary-card"
                            >
                                {thumbUrl && (
                                    <img
                                        src={thumbUrl}
                                        alt={news.title}
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                    />
                                )}
                                <span className="news-card-headline">{news.title}</span>
                                <span className="news-card-meta">
                                    {news.publisher && <span>{news.publisher}</span>}
                                    {news.publisher && news.providerPublishTime && (
                                        <span className="news-card-meta-dot">·</span>
                                    )}
                                    {news.providerPublishTime && (
                                        <span>{getRelativeTime(news.providerPublishTime)}</span>
                                    )}
                                </span>
                            </a>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default NewsData;
