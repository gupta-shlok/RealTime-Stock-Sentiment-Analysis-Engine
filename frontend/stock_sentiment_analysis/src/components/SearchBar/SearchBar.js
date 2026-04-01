import React, { useState } from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import { useNavigate } from 'react-router-dom';
import './SearchBar.css';

const SearchBar = ({ onSearch }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const navigate = useNavigate();

    const options = [
        'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AIG', 'AMD', 'AMGN', 'AMT', 'AMZN',
        'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'BRK-B', 'BX',
        'C', 'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO',
        'CVS', 'CVX', 'DE', 'DHR', 'DIS', 'DUK', 'EMR', 'EOG', 'EQIX', 'EXC',
        'F', 'FDX', 'GD', 'GE', 'GEV', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS',
        'HD', 'HON', 'IBM', 'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KHC', 'KO',
        'LIN', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META',
        'MMM', 'MO', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NOW', 'NVDA',
        'ORCL', 'PEP', 'PFE', 'PG', 'PLTR', 'PM', 'PSA', 'PYPL', 'QCOM', 'RTX',
        'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT', 'TMO', 'TMUS', 'TXN', 'UNH',
        'UNP', 'UPS', 'USB', 'V', 'VZ', 'WFC', 'WMT', 'XOM',
    ];

    return (
        <Autocomplete
            disableClearable
            id="stock-search"
            options={options}
            getOptionLabel={(option) => option}
            value={searchTerm}
            onChange={(event, newValue) => {
                setSearchTerm(newValue);
                if (newValue) navigate(`/stock/${newValue}`);
            }}
            componentsProps={{
                paper: {
                    sx: {
                        backgroundColor: 'var(--bg-elevated)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border)',
                        borderRadius: '0 0 8px 8px',
                        mt: '-1px',
                    },
                },
            }}
            sx={{ width: 320 }}
            renderInput={(params) => (
                <TextField
                    {...params}
                    size="small"
                    placeholder="Search ticker..."
                    sx={{
                        '& .MuiOutlinedInput-root': {
                            borderRadius: '8px',
                            backgroundColor: 'var(--bg-elevated)',
                            color: 'var(--text-primary)',
                            '& fieldset': { borderColor: 'var(--border)' },
                            '&:hover fieldset': { borderColor: 'var(--text-disabled)' },
                            '&.Mui-focused fieldset': { borderColor: 'var(--accent-blue)' },
                        },
                        '& .MuiInputBase-input': {
                            color: 'var(--text-primary)',
                            fontSize: '0.875rem',
                        },
                        '& .MuiInputBase-input::placeholder': {
                            color: 'var(--text-secondary)',
                            opacity: 1,
                        },
                        '& .MuiSvgIcon-root': { color: 'var(--text-secondary)' },
                    }}
                />
            )}
        />
    );
};

export default SearchBar;
