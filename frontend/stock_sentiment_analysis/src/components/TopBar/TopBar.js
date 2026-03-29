import React, { useState, useContext } from 'react';
import SearchBar from '../SearchBar/SearchBar';
import { Link, useLocation } from 'react-router-dom';
import {
    LinearProgress,
    IconButton,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import { StockDataContext } from '../../context/StockDataContext';
import './TopBar.css';

const INTERVAL_OPTIONS = [
    { label: '5 min', value: 300000 },
    { label: '10 min', value: 600000 },
    { label: '30 min', value: 1800000 },
];

const TopBar = () => {
    const location = useLocation();
    const isCustomSentimentPage = location.pathname === '/custom-sentiment';

    const { isRefreshing, lastUpdated, refreshInterval, setRefreshInterval } = useContext(StockDataContext);

    const [settingsOpen, setSettingsOpen] = useState(false);
    const [pendingInterval, setPendingInterval] = useState(refreshInterval);

    const handleOpenSettings = () => {
        setPendingInterval(refreshInterval);
        setSettingsOpen(true);
    };

    const handleSaveSettings = () => {
        setRefreshInterval(pendingInterval);
        setSettingsOpen(false);
    };

    const formatLastUpdated = (date) => {
        if (!date) return '';
        return `Last updated ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
    };

    return (
        <>
            {isRefreshing && (
                <LinearProgress
                    sx={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: 2,
                        zIndex: 9999,
                        backgroundColor: 'rgba(59,130,246,0.2)',
                        '& .MuiLinearProgress-bar': { backgroundColor: '#3b82f6' },
                    }}
                />
            )}
            <div className="header">
                <a href="/">
                    <img src="download.png" alt="Logo" id="logo" />
                </a>
                <SearchBar />
                <div className="topbar-right">
                    <span className="last-updated-text">
                        {isRefreshing ? 'Updating\u2026' : formatLastUpdated(lastUpdated)}
                    </span>
                    <IconButton
                        onClick={handleOpenSettings}
                        size="small"
                        aria-label="Refresh interval settings"
                        sx={{ color: '#94a3b8', ml: 1 }}
                    >
                        <SettingsIcon fontSize="small" />
                    </IconButton>
                    <nav className="custom-navbar">
                        <Link
                            to={isCustomSentimentPage ? '/' : '/custom-sentiment'}
                            className="custom-sentiment-button"
                        >
                            {isCustomSentimentPage ? 'Home' : 'Custom Sentiment'}
                        </Link>
                    </nav>
                </div>
            </div>

            <Dialog
                open={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                PaperProps={{ sx: { backgroundColor: '#1e293b', color: '#f1f5f9', minWidth: 320 } }}
            >
                <DialogTitle sx={{ color: '#f1f5f9', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    Settings
                </DialogTitle>
                <DialogContent sx={{ pt: 3 }}>
                    <FormControl fullWidth size="small">
                        <InputLabel sx={{ color: '#94a3b8' }}>Refresh interval</InputLabel>
                        <Select
                            value={pendingInterval}
                            label="Refresh interval"
                            onChange={(e) => setPendingInterval(e.target.value)}
                            sx={{
                                color: '#f1f5f9',
                                '& .MuiOutlinedInput-notchedOutline': { borderColor: '#475569' },
                                '& .MuiSvgIcon-root': { color: '#94a3b8' },
                            }}
                        >
                            {INTERVAL_OPTIONS.map(opt => (
                                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions sx={{ borderTop: '1px solid rgba(255,255,255,0.08)', px: 3, pb: 2 }}>
                    <Button onClick={() => setSettingsOpen(false)} sx={{ color: '#94a3b8' }}>
                        Keep Current Settings
                    </Button>
                    <Button onClick={handleSaveSettings} variant="contained" sx={{ backgroundColor: '#3b82f6' }}>
                        Save Settings
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
};

export default TopBar;
