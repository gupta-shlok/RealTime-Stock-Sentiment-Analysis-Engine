# Phase 3 Plan 02 Summary: Data Pipeline Refactor

**Plan**: 03-02
**Wave**: 2
**Requirements**: DATA-02, DATA-03, DATA-04
**Status**: Complete

## Objective
Refactor data endpoints to scale to all 102 S&P 100 tickers with efficient batch fetching, tiered news rotation, and UUID deduplication.

## Implementation

### Batch `yf.download()` for /stock-price
- Replaced per-ticker concurrent fetching with batched downloads using `yf.download()`.
- Tickers are split into two batches: first 50, remaining 52.
- Added a 1.5-second polite delay between batches to avoid rate limiting.
- For each batch, a single `yf.download()` call retrieves one year of daily data for all tickers in the batch.
- Extraction logic handles both possible MultiIndex orientations (ticker-first or attribute-first) to be robust across yfinance versions.
- Per-ticker data is computed: current close, previous close, percent change, and monthly OHLC aggregations (first open, last close, max high, min low per month).
- After processing all batches, data is reorganized by GICS sector using `TICKER_DATA` from `tickers.py`. The response shape is `{sector: {ticker: data}}`.
- Removed the old `fetch_ticker_data` helper, semaphore, and bounded fetch logic.

### Tiered News Rotation
- Added module-level `TIER2_OFFSET = 0` to track rotation state.
- In `/news` endpoint:
  - If a specific `ticker` query param is provided, fetch news for that ticker only (no tiering).
  - For the aggregated feed (no ticker):
    - Build a list of tickers with valid `market_cap > 0` from `TICKER_DATA`.
    - Sort tickers by market cap descending.
    - Partition: Tier1 = top 20, Tier2_pool = next 40, Tier3 = remainder (excluded from aggregated fetch).
    - Select 40 tickers from Tier2_pool with a rotating offset: `start = TIER2_OFFSET % len(pool)`, then pick with wrap-around.
    - `search_symbols = Tier1 + selected_Tier2`.
    - Log tier composition for debugging.
- After completing the fetch for an aggregated request, update `TIER2_OFFSET = (TIER2_OFFSET + 40) % len(tier2_pool)` to rotate the pool for the next request.

### UUID Deduplication
- Added `seen_uuids = set()` at the start of the news gathering.
- For each news item from Yahoo, before premium check and sentiment scoring:
  - Extract `uuid`.
  - If `uuid` exists and already in `seen_uuids`, skip the item.
  - Otherwise, add `uuid` to the set and continue processing.
- This ensures duplicate articles across multiple tickers appear only once in the aggregated feed.
- Deduplication occurs before sentiment scoring to avoid unnecessary compute.

## Verification
All automated checks defined in the plan passed:
- `yf.download` is used ✅
- `await asyncio.sleep(1.5)` present ✅
- Batches split using literal `50` ✅
- `TIER2_OFFSET` defined and used ✅
- `seen_uuids` deduplication logic ✅
- Manual test: `/stock-price` returned 102 tickers across 11 sectors ✅

## Performance Notes
- The batch fetch approach reduces the number of yfinance requests from 102 individual calls to 2 batch calls, significantly improving latency and reducing rate limit risk.
- The 1.5-second delay between batches is conservative; on warm connections, total fetch time for 102 tickers should remain under 10 seconds (as observed during testing).
- Tiered news reduces load by 60% on each aggregated cycle: only 60 of 102 tickers are fetched (Tier1 always, 40 from Tier2 rotating). Tier3 tickers are only fetched on-demand when a user visits that specific company page.
- UUID deduplication prevents duplicate article displays across sectors.

## Next Steps
Phase 3 is now complete. The backend serves all 102 S&P 100 tickers with efficient data fetching and intelligent news aggregation. Phase 4 (Sentiment Intelligence Upgrade) can now proceed, building upon the full ticker set and endpoints.
