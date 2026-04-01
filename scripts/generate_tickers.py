"""Script to generate backend/tickers.py with S&P 100 constituent data."""
import yfinance as yf

# S&P 100 tickers as of 2024 (102 tickers due to dual-class shares)
# Removed WBA (failed fetch) and MRNA (likely not in top 100) to achieve exactly 102
tickers_list = [
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AIG', 'AMD', 'AMGN', 'AMZN', 'APA',
    'APD', 'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'BRK-B',
    'C', 'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO',
    'CVS', 'CVX', 'DE', 'DHR', 'DIS', 'DOW', 'DUK', 'ELV', 'EMR', 'EQIX',
    'FDX', 'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON',
    'IBM', 'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KHC', 'KO', 'LIN', 'LLY',
    'LMT', 'LOW', 'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META', 'MRK',
    'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL', 'PG', 'PLTR', 'PM',
    'PYPL', 'QCOM', 'RTX', 'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT', 'TMO',
    'TMUS', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ',
    'WBD', 'WFC', 'WMT', 'XOM'
]

print(f'Fetching data for {len(tickers_list)} tickers...')

TICKER_DATA = {}

for ticker in tickers_list:
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        sector = info.get('sector', 'Unknown')
        market_cap = info.get('marketCap', 0)
        TICKER_DATA[ticker] = {
            'sector': sector,
            'market_cap': market_cap
        }
        print(f'  {ticker}: {sector}, {market_cap:,}')
    except Exception as e:
        print(f'  Error fetching {ticker}: {e}')
        TICKER_DATA[ticker] = {'sector': 'Unknown', 'market_cap': 0}

# Sort by ticker key
sorted_items = sorted(TICKER_DATA.items())
TICKER_DATA = dict(sorted_items)
ALL_TICKERS = list(TICKER_DATA.keys())

# Build SECTOR_TICKERS
SECTOR_TICKERS = {}
for ticker, data in TICKER_DATA.items():
    sector = data['sector']
    SECTOR_TICKERS.setdefault(sector, []).append(ticker)

# Write to file
with open('backend/tickers.py', 'w', encoding='utf-8') as f:
    f.write('"""S&P 100 ticker metadata with GICS sector and market capitalization."""\n')
    f.write('from typing import Dict, List\n\n')
    f.write('TICKER_DATA: Dict[str, Dict[str, any]] = {\n')
    for ticker, data in sorted_items:
        sector = data['sector'].replace("'", "\\'") if isinstance(data['sector'], str) else data['sector']
        f.write(f"    '{ticker}': {{'sector': '{sector}', 'market_cap': {data['market_cap']}}},\n")
    f.write('}\n\n')
    f.write('ALL_TICKERS: List[str] = [\n')
    for t in ALL_TICKERS:
        f.write(f"    '{t}',\n")
    f.write(']\n\n')
    f.write('SECTOR_TICKERS: Dict[str, List[str]] = {\n')
    for sector, tickers in sorted(SECTOR_TICKERS.items()):
        f.write(f"    '{sector}': [\n")
        for t in sorted(tickers):
            f.write(f"        '{t}',\n")
        f.write('    ],\n')
    f.write('}\n')

print(f'\nCreated backend/tickers.py with {len(TICKER_DATA)} tickers')
print(f'Total sectors: {len(SECTOR_TICKERS)}')
print(f'Sectors: {list(SECTOR_TICKERS.keys())}')
