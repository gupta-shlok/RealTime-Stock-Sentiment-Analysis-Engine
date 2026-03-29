import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
import { getStockData } from '../apis/api';
import useInterval from '../hooks/useInterval';

export const StockDataContext = createContext({
    stocks: [],
    loading: true,
    isRefreshing: false,
    error: null,
    lastUpdated: null,
    refresh: () => {},
    refreshInterval: 600000,
    setRefreshInterval: () => {},
});

export const StockDataProvider = ({ children }) => {
    const [stocks, setStocks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [refreshInterval, setRefreshIntervalState] = useState(() => {
        const stored = localStorage.getItem('sentiment_refresh_interval');
        return stored ? parseInt(stored, 10) : 600000;
    });
    const isRefreshingRef = useRef(false);

    const fetchData = useCallback(async (isBackground = false) => {
        // In-flight guard: skip if already fetching
        if (isRefreshingRef.current) return;

        isRefreshingRef.current = true;
        if (isBackground) {
            setIsRefreshing(true);
        } else {
            setLoading(true);
        }
        setError(null);

        try {
            const data = await getStockData();
            const stockArray = Object.entries(data).map(([name, stockInfo]) => ({ name, ...stockInfo }));
            setStocks(stockArray);
            setLastUpdated(new Date());
            setError(null);
        } catch (err) {
            setError('Could not load stock data. Check your connection and try again.');
        } finally {
            isRefreshingRef.current = false;
            setLoading(false);
            setIsRefreshing(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchData(false);
    }, [fetchData]);

    // Auto-refresh via useInterval
    const refresh = useCallback(() => fetchData(true), [fetchData]);

    useInterval(refresh, refreshInterval);

    const setRefreshInterval = useCallback((ms) => {
        localStorage.setItem('sentiment_refresh_interval', String(ms));
        setRefreshIntervalState(ms);
    }, []);

    return (
        <StockDataContext.Provider value={{
            stocks,
            loading,
            isRefreshing,
            error,
            lastUpdated,
            refresh,
            refreshInterval,
            setRefreshInterval,
        }}>
            {children}
        </StockDataContext.Provider>
    );
};
