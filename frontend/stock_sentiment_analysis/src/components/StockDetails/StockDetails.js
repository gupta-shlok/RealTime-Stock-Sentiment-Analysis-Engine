// components/StockDetails.js
import React from 'react';
import { Link } from 'react-router-dom';
import './StockDetails.css';

const StockDetails = ({ stock }) => {
    const pct = stock.percent_change;
    const isPositive = pct >= 0;
    return (
        <div className="ticker-cell">
            <Link to={`/stock/${stock.name}`} className="ticker-symbol">{stock.name}</Link>
            <span className="ticker-price">${(stock.current_close ?? 0).toFixed(2)}</span>
            <span className={`pct-badge ${isPositive ? 'pct-badge--up' : 'pct-badge--down'}`}>
                {isPositive ? '+' : ''}{(pct ?? 0).toFixed(2)}%
            </span>
        </div>
    );
};

export default StockDetails;
