import React from 'react';
import SentimentHeatmap from '../SentimentHeatmap/SentimentHeatmap';
import SectorSentimentRow from '../SectorSentimentRow/SectorSentimentRow';
import NewsContent from '../NewsContent/NewsContent';
import './HomePage.css';

const HomePage = () => {
    return (
        <div className="home-page">
            <SentimentHeatmap />
            <SectorSentimentRow />
            <NewsContent />
        </div>
    );
};

export default HomePage;
