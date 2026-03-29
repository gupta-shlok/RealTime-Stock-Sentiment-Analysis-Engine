import React, { useState, useEffect } from 'react';
import { getSectorSentiment } from '../../apis/api';
import { Skeleton, Button } from '@mui/material';
import './SectorSentimentRow.css';

// Reuse sentiment color for sector card accent
function getSentimentColor(score) {
    if (score === null || score === undefined) return '#475569';
    const s = Math.max(-1, Math.min(1, score));
    if (s >= 0.4) return '#16a34a';
    if (s >= 0) return '#4ade80';
    if (s >= -0.4) return '#f87171';
    return '#dc2626';
}

const SectorSentimentRow = () => {
    const [sectors, setSectors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchSectors = () => {
        setLoading(true);
        setError(null);
        getSectorSentiment()
            .then(data => {
                setSectors(data.sectors || []);
                setLoading(false);
            })
            .catch(() => {
                setError('Could not load sector sentiment data.');
                setLoading(false);
            });
    };

    useEffect(() => { fetchSectors(); }, []);

    if (loading) {
        return (
            <div className="sector-row">
                {[1, 2, 3, 4, 5].map(i => (
                    <Skeleton key={i} variant="rectangular" height={80} sx={{ borderRadius: '8px', bgcolor: 'rgba(255,255,255,0.08)', flex: '1 1 150px' }} />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="sector-row-error">
                <p>{error}</p>
                <Button variant="outlined" size="small" onClick={fetchSectors} sx={{ color: '#94a3b8', borderColor: '#475569', mt: 1 }}>
                    Retry
                </Button>
            </div>
        );
    }

    return (
        <div className="sector-row">
            {sectors.map(sector => {
                const color = getSentimentColor(sector.avg_score);
                const scoreStr = sector.avg_score !== null
                    ? (sector.avg_score >= 0 ? '+' : '') + sector.avg_score.toFixed(2)
                    : 'N/A';
                return (
                    <div key={sector.sector} className="sector-card glass-card">
                        <span className="section-label">{sector.sector}</span>
                        <span className="sector-score" style={{ color }}>{scoreStr}</span>
                        <span className="sector-count">{sector.stock_count} stocks</span>
                    </div>
                );
            })}
        </div>
    );
};

export default SectorSentimentRow;
