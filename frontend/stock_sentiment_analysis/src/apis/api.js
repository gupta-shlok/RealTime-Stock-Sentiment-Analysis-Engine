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
