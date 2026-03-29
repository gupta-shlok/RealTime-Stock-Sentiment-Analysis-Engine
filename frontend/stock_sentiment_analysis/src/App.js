import React from 'react';
import HomePage from './components/HomePage/HomePage';
import {StockDataProvider} from "./context/StockDataContext";
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import CustomSentiment from './components/CustomSentiment/CustomSentiment';
import CompanyPage from './components/CompanyPage/CompanyPage';
import StockChart from './components/StockChart/StockChart';
import './App.css';
import TopBar from './components/TopBar/TopBar';

const App = () => {
    return (
        // <StockDataProvider>
        //     <HomePage />
        // </StockDataProvider>
        <StockDataProvider>
            <Router>
                <TopBar />
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/custom-sentiment" element={<CustomSentiment />} />
                    <Route path="/stock/:ticker" element={<CompanyPage />} />
                </Routes>
                <StockChart />
            </Router>
        </StockDataProvider>
    );
};

export default App;
