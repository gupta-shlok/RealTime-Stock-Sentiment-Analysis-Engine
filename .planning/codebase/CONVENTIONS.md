# Coding Conventions

**Analysis Date:** 2026-03-26

## File and Folder Naming Conventions

**React Components:**
- Component directories use PascalCase matching the component name exactly: `CompanyPage/`, `SearchBar/`, `TopBar/`, `StockChart/`, `NewsItem/`, `CustomSentiment/`
- Component JS files match the directory name: `CompanyPage/CompanyPage.js`, `SearchBar/SearchBar.js`
- Component CSS files also match the directory name: `CompanyPage/CompanyPage.css`, `SearchBar/SearchBar.css`
- Every component directory bundles its own JS and CSS file — no shared component-level stylesheets

**Non-component files:**
- Utility files use camelCase: `getStockData.js`
- Context files use PascalCase with "Context" suffix: `StockDataContext.js`
- API files use lowercase: `api.js`
- Python backend files use snake_case: `fetch_latest_news.py`, `news_preprocess.py`, `create_add_monthly_stock_data.py`, `SentimentAnalysis.py` (one exception uses PascalCase)

**Directory layout:**
```
src/
  apis/          # HTTP client functions
  components/    # Feature components, each in its own PascalCase subdirectory
  context/       # React Context providers
  utils/         # Pure utility functions
```

## Component Structure Patterns

**Functional components exclusively.** No class components are present anywhere in the frontend.

**Standard component shape (presentational):**
```js
// components/StockDetails.js
import React from 'react';
import { Link } from 'react-router-dom';
import './StockDetails.css';

const StockDetails = ({ stock }) => {
    return (
        <div className="stock-details">
            ...
        </div>
    );
};

export default StockDetails;
```
Examples: `src/components/StockDetails/StockDetails.js`, `src/components/NewsItem/NewsItem.js`, `src/components/CompanyTicker/CompanyTicker.js`, `src/components/Footer/Footer.js`

**Data-fetching component shape (container):**
Declares local state with `useState`, fires async fetch in `useEffect`, renders loading state while waiting, renders empty state on zero results, then renders content.
```js
const NewsData = () => {
    const [newsItems, setNewsItems] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getNewsData().then((data) => {
            ...
            setLoading(false);
        }).catch(() => {
            setLoading(false);
        });
    }, []);

    if (loading) { return (...); }
    if (newsItems.length === 0) { return (...); }
    return (...);
};
```
Examples: `src/components/NewsData/NewsData.js`, `src/components/CompanyPage/CompanyPage.js`

**Context-consuming component shape:**
Reads shared stock data via `useContext(StockDataContext)` at the top of the component body, then renders directly from that data.
Examples: `src/components/StockChart/StockChart.js`, `src/components/TopCompanies/TopCompanies.js`

**Page/layout component shape:**
Thin wrappers that assemble named child components with minimal logic.
```js
const HomePage = () => {
    return (
        <div>
            <StockChart />
            <NewsContent />
            <Footer />
        </div>
    );
};
```
Examples: `src/components/HomePage/HomePage.js`, `src/components/NewsContent/NewsContent.js`

**Naming:** Component function names match the file and directory name. One exception: `CustomSentiment.js` exports `CustomSentimentPage` (function name diverges from file/directory name).

## Import and Export Patterns

**Import order (observed pattern):**
1. React and React hooks (`import React, { useContext, useEffect, useState } from 'react'`)
2. React Router hooks/components (`import { useParams, Link } from 'react-router-dom'`)
3. Context imports (`import { StockDataContext } from '../../context/StockDataContext'`)
4. Internal component imports (`import NewsItem from '../NewsItem/NewsItem'`)
5. External library imports (`import { LineChart, ... } from 'recharts'`)
6. API imports (`import { getNewsData } from '../../apis/api'`)
7. CSS import last (`import './CompanyPage.css'`)

**Exports:** Every component uses `export default ComponentName` at the bottom of the file. Named exports are only used for context values (`export const StockDataContext`, `export const StockDataProvider`) and API functions (`export const getStockData`, `export const getNewsData`).

**Path style:** All imports use relative paths (`../../context/StockDataContext`). No path aliases are configured.

**No barrel/index files.** Each import references the full path including the file name, e.g., `'../NewsItem/NewsItem'` not `'../NewsItem'`.

## CSS and Styling Conventions

**Architecture:** Global design tokens in `src/App.css` via CSS custom properties on `:root`. Component-scoped styles in co-located `.css` files.

**Global CSS variables (defined in `src/App.css`):**
```css
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-color: #3b82f6;
  --accent-hover: #2563eb;
  --glass-bg: rgba(30, 41, 59, 0.7);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```
All component stylesheets consume these variables. Hard-coded hex values also appear alongside variables (e.g., `#10b981`, `#ef4444`, `#94a3b8`), particularly for semantic sentiment colors.

**Glassmorphism design system:** Shared visual language across all components:
- `.glass-panel`: sticky header and page-level containers — defined in `App.css`, applied in `CompanyPage.js`, `TopBar.js`
- `.glass-card`: internal card elements — defined inline in `CompanyPage.css`
- Properties: `backdrop-filter: blur(12px)`, `background: var(--glass-bg)`, `border: 1px solid var(--glass-border)`, `border-radius: 12px`

**CSS class naming:** kebab-case throughout. BEM is not used. Class names are semantically descriptive: `.company-title-row`, `.sentiment-badge`, `.ticker-change`, `.news-image-container`.

**Sentiment color convention:** Green `#10b981` = bullish/positive, Red `#ef4444` = bearish/negative, Slate `#94a3b8` = neutral. Applied via modifier classes: `.bullish`, `.bearish`, `.neutral` on badges and labels.

**Hover transitions:** Standardized pattern — `transition: all 0.3s ease` with `transform: translateY(-Xpx)` lift effect on interactive cards. Used in `.news-item:hover`, `.custom-sentiment-button:hover`, `.submit-button:hover`.

**MUI overriding:** `SearchBar.css` overrides Material UI component internals directly with deep CSS selectors (`div.MuiAutocomplete-root div.MuiOutlinedInput-root`) to match the dark glass theme.

**Typography:** Inter from Google Fonts, loaded in `App.css`. Monospace font (JetBrains Mono) referenced in `CompanyPage.css` for price figures but not loaded via Google Fonts import.

**No CSS Modules, no styled-components, no Tailwind.** Plain CSS files only.

**Responsive design:** Only `CompanyPage.css` includes a `@media (max-width: 768px)` breakpoint. Other components have no responsive breakpoints.

## State Management Patterns

**Global state:** A single React Context — `StockDataContext` in `src/context/StockDataContext.js`. Wraps the entire app in `App.js` via `<StockDataProvider>`. Stores stock price data fetched once on mount from the `/stock-price` API endpoint. Provides a transformed `stockArray` (from object to array of `{ name, ...data }` entries) to all consumers.

**Local state:** `useState` hooks for component-specific async data and loading flags. Pattern is always paired: one state for the data, one `boolean` for loading.
```js
const [newsItems, setNewsItems] = useState([]);
const [loading, setLoading] = useState(true);
```
Examples: `NewsData.js`, `CompanyPage.js`, `CustomSentiment.js`

**No Redux, Zustand, or any external state library.** Context + useState is the complete state solution.

**Data flows one direction:** Context provides stock data downward. Components fetch their own additional data (e.g., `CompanyPage` fetches ticker-specific news locally, independent of context).

**Commented-out code present:** `App.js` has a commented-out `<StockDataProvider>` + `<HomePage>` block from an earlier structural iteration, indicating refactoring occurred without cleanup.

## API Call Patterns

**HTTP client:** `axios` exclusively. Used in `src/apis/api.js` and directly inside `src/components/CustomSentiment/CustomSentiment.js`.

**Centralized API module:** `src/apis/api.js` exports named functions `getStockData()` and `getNewsData(ticker?)`. Components import from this module, not from axios directly — except `CustomSentiment.js`, which imports and uses axios inline (inconsistency).

**Duplicate utility:** `src/utils/getStockData.js` contains an older copy of `getStockData()` pointing to a different API Gateway URL (`ip8z0jodq4...` vs. `pcg7asbzqd...` in `api.js`). It is not imported anywhere in the active codebase.

**Environment variable pattern:**
```js
let url = process.env.REACT_APP_API_URL
    ? `${process.env.REACT_APP_API_URL}/stock-price`
    : "https://pcg7asbzqd.execute-api.us-east-1.amazonaws.com/prod/stock-price";
```
All API calls check `process.env.REACT_APP_API_URL` first, falling back to a hardcoded production AWS API Gateway URL.

**Promise chaining style:** `.then()` / `.catch()` used in `api.js` and `StockDataContext.js`. `async/await` used in `CustomSentiment.js`. No consistent style across the codebase.

**Backend API functions:** Python FastAPI in `backend/main.py`. Functions are at module level — no class-based organization. In-memory dict cache (`cache: Dict[str, Any]`) used to avoid redundant fetches within a single server session.

## Error Handling Conventions

**Frontend:**
- API errors in `api.js` are caught and re-thrown as generic `new Error('Something went wrong')` strings, discarding the original error details.
- Component-level catch blocks set `loading` to `false` silently — no error state is surfaced to the user UI. Example in `NewsData.js`: `.catch(() => { setLoading(false); })`.
- `CompanyPage.js` logs to `console.error` on fetch failure but renders no error message to the user.
- `CustomSentiment.js` is the one exception — it stores error messages in result state and renders them: `setResult({ error: "Failed to analyze sentiment." })`.
- `console.log` and `console.error` calls are present throughout API functions and are not conditionally disabled.

**Backend (Python):**
- Route handlers use try/except blocks around external calls (yfinance, Yahoo Finance HTTP, sentiment models).
- Errors are printed with `flush=True` for immediate Docker log output: `print(f"Error fetching stock data for {ticker}: {e}", flush=True)`.
- Failed ticker fetches are skipped silently (continue), not surfaced to the API response.
- The `/analyze-custom` endpoint returns `{"error": str(e)}` on exception instead of an HTTP error status code.
- No HTTP exception classes (e.g., `HTTPException`) are raised in any route handler.

---

*Convention analysis: 2026-03-26*
