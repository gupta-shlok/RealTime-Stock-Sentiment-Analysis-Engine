// api.js
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL;

export const getStockData = () => {
    const url = `${API_BASE}/stock-price`;

    return axios.get(url)
        .then((response) => {
            return response.data;
        })
        .catch((error) => {
            console.error('getStockData error:', error);
            throw new Error('Failed to fetch stock data');
        });
};

export const getNewsData = (ticker = "") => {
    const baseUrl = `${API_BASE}/news`;
    const url = ticker ? `${baseUrl}?ticker=${encodeURIComponent(ticker)}` : baseUrl;

    return axios.get(url)
        .then((response) => {
            return response.data;
        })
        .catch((error) => {
            console.error('getNewsData error:', error);
            throw new Error('Failed to fetch news data');
        });
};

export const getSectorSentiment = () => {
    const url = `${API_BASE}/sector-sentiment`;
    return axios.get(url)
        .then(response => response.data)
        .catch(error => {
            console.error('getSectorSentiment error:', error);
            throw new Error('Failed to fetch sector sentiment data');
        });
};

export const getSentimentTrends = (ticker, window = '7d') => {
    const url = `${API_BASE}/sentiment-trends?ticker=${encodeURIComponent(ticker)}&window=${window}`;
    return axios.get(url)
        .then(response => response.data)
        .catch(error => {
            console.error('getSentimentTrends error:', error);
            throw new Error(`Failed to fetch sentiment trends for ${ticker}`);
        });
};

export const getStockNarrative = (ticker) => {
    const url = `${API_BASE}/stock-narrative/${encodeURIComponent(ticker)}`;
    return axios.get(url)
        .then(response => response.data)
        .catch(error => {
            console.error('getStockNarrative error:', error);
            throw new Error(`Failed to fetch narrative for ${ticker}`);
        });
};
