// components/StockChart.js
import React, { useContext } from 'react';
import { StockDataContext } from '../../context/StockDataContext';
import StockDetails from '../StockDetails/StockDetails';
import './StockChart.css';

const StockChart = () => {
    const { stocks } = useContext(StockDataContext);

    if (!stocks || stocks.length === 0) return null;

    return (
        <div className="ticker-strip">
            <div className="ticker-strip-track">
                {stocks.map((stock, index) => (
                    <StockDetails key={index} stock={stock} />
                ))}
                {/* Duplicate for seamless loop */}
                {stocks.map((stock, index) => (
                    <StockDetails key={`dup-${index}`} stock={stock} />
                ))}
            </div>
        </div>
    );
};

export default StockChart;
