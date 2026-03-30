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
    Box,
    Typography,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
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

    const { isRefreshing, lastUpdated, refreshInterval, setRefreshInterval, theme, setTheme } = useContext(StockDataContext);

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
                        '& .MuiLinearProgress-bar': { backgroundColor: 'var(--accent-blue)' },
                    }}
                />
            )}
            <div className="header">
                <span className="topbar-brand">StockSentimentSense</span>
                <SearchBar />
                <div className="topbar-right">
                    <span className="last-updated-text">
                        {isRefreshing ? 'Updating\u2026' : formatLastUpdated(lastUpdated)}
                    </span>
                    <IconButton
                        onClick={handleOpenSettings}
                        size="small"
                        aria-label="Refresh interval settings"
                        sx={{ color: 'var(--text-secondary)', ml: 1 }}
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
                PaperProps={{ sx: { backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', minWidth: 320 } }}
            >
                <DialogTitle sx={{ color: 'var(--text-primary)', borderBottom: '1px solid var(--border)' }}>
                    Settings
                </DialogTitle>
                <DialogContent sx={{ pt: 4 }}>
                    <FormControl fullWidth size="small" sx={{ mt: 1 }}>
                        <InputLabel sx={{
                            color: 'var(--text-secondary)',
                            '&.Mui-focused': { color: 'var(--accent-blue)' },
                            '&.MuiFormLabel-filled': { color: 'var(--text-secondary)' },
                            backgroundColor: 'var(--bg-surface)',
                            px: 0.5,
                        }}>Refresh interval</InputLabel>
                        <Select
                            value={pendingInterval}
                            label="Refresh interval"
                            onChange={(e) => setPendingInterval(e.target.value)}
                            sx={{
                                color: 'var(--text-primary)',
                                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--text-disabled)' },
                                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--text-secondary)' },
                                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--accent-blue)' },
                                '& .MuiSvgIcon-root': { color: 'var(--text-secondary)' },
                            }}
                            MenuProps={{ PaperProps: { sx: { backgroundColor: 'var(--bg-surface)' } } }}
                        >
                            {INTERVAL_OPTIONS.map(opt => (
                                <MenuItem key={opt.value} value={opt.value} sx={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', '&:hover': { backgroundColor: 'var(--bg-elevated)' }, '&.Mui-selected': { backgroundColor: '#1d4ed8' }, '&.Mui-selected:hover': { backgroundColor: '#2563eb' } }}>{opt.label}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <Box sx={{ mt: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            Theme
                        </Typography>
                        <IconButton
                            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                            size="small"
                            sx={{ color: 'var(--text-secondary)' }}
                            aria-label="Toggle theme"
                        >
                            {theme === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
                        </IconButton>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ borderTop: '1px solid var(--border)', px: 3, pb: 2 }}>
                    <Button onClick={() => setSettingsOpen(false)} sx={{ color: 'var(--text-secondary)' }}>
                        Keep Current Settings
                    </Button>
                    <Button onClick={handleSaveSettings} variant="contained" sx={{ backgroundColor: 'var(--accent-blue)' }}>
                        Save Settings
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
};

export default TopBar;
