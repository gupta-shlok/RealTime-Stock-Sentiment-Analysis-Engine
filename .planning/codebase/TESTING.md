# Testing Patterns

**Analysis Date:** 2026-03-26

## Test Framework

**Runner:**
- Jest (bundled via `react-scripts` 5.0.1 / Create React App)
- No separate `jest.config.js` — configuration is embedded in CRA defaults
- No `vitest`, `mocha`, or other runner present

**Assertion Library:**
- `@testing-library/jest-dom` 5.17.0 — extends Jest matchers with DOM-specific assertions (e.g., `toBeInTheDocument`)

**Component Testing:**
- `@testing-library/react` 13.4.0 — `render`, `screen` utilities
- `@testing-library/user-event` 13.5.0 — installed but not used in any current test

**Run Commands:**
```bash
# From frontend/stock_sentiment_analysis/
npm test              # Interactive watch mode (CRA default)
npm test -- --watchAll=false   # Single run, no watch (CI usage)
npm test -- --coverage         # Generate coverage report
```

**ESLint config for tests:**
```json
"eslintConfig": {
  "extends": ["react-app", "react-app/jest"]
}
```
Configured in `frontend/stock_sentiment_analysis/package.json`. No `.eslintrc` file present.

## Test File Locations and Naming

**Current test files:**
- `frontend/stock_sentiment_analysis/src/App.test.js` — the only test file in the entire project

**Naming convention:**
- CRA convention: `[ComponentName].test.js` co-located alongside the source file in `src/`
- `App.test.js` sits directly in `src/` alongside `App.js`

**Setup file:**
- `frontend/stock_sentiment_analysis/src/setupTests.js` — imported automatically by CRA before every test run
- Contains only: `import '@testing-library/jest-dom'`

**No test files exist** inside any component subdirectory (`src/components/*/`) or in the `src/apis/`, `src/context/`, or `src/utils/` directories.

**Backend:**
- Zero Python test files. No `pytest`, `unittest`, or any test runner configured. No `tests/` directory in `backend/`.

## Types of Tests Present

**Unit tests:** Not present (no isolated function or module tests)

**Integration tests:** Not present

**Component tests:** One test exists in `src/App.test.js`:
```js
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
```
This is the unmodified Create React App scaffold test. It searches for the text "learn react" which does not exist anywhere in the actual application — the test will **fail** when run against the current codebase. It has never been updated to reflect real application content.

**E2E tests:** Not present. No Cypress, Playwright, or Selenium configuration.

**Backend tests:** Not present. No pytest files, no `conftest.py`, no test fixtures.

## Test Coverage Level

**Effective coverage: 0%**

The single existing test (`App.test.js`) is a broken scaffold that does not test actual application behavior. No component, context, API function, utility, or backend route has any test coverage.

**Coverage tooling:** Jest's built-in coverage reporter (via `istanbul`) is available through CRA but has never been run or configured with thresholds. There is no coverage configuration in `package.json` (no `"jest"` key with `coverageThreshold`).

## How to Run Tests

```bash
# Navigate to the frontend project root
cd frontend/stock_sentiment_analysis

# Run tests in watch mode (default)
npm test

# Run once without watch (useful in CI)
CI=true npm test

# Run with coverage output
npm test -- --coverage --watchAll=false
```

There is no `Makefile`, shell script, or CI pipeline configuration that automates test execution. The `amplify.yml` file does not include a test step.

**Note:** Running `npm test` against the current codebase will produce a failure because `App.test.js` searches for text that does not exist in the rendered output (`/learn react/i`). Additionally, `App.js` imports `StockDataProvider` which calls the live API on render, which will fail or timeout in a test environment without mocking.

## Notable Gaps in Testing

**Broken scaffold test:**
- `src/App.test.js` asserts `/learn react/i` text that was never updated from the CRA template. This must be replaced or deleted before any meaningful test suite can be established.

**No API mocking infrastructure:**
- `src/apis/api.js` makes real axios HTTP calls with no mock layer. Tests that render any data-fetching component (`NewsData`, `CompanyPage`, `StockChart`, `TopCompanies`) will hit live AWS API Gateway endpoints or fail with network errors. No `msw` (Mock Service Worker), `axios-mock-adapter`, or Jest module mocks are configured.

**No context test utilities:**
- `StockDataContext` wraps the entire app and fetches on mount. There is no test helper or mock provider to inject known stock data for component testing.

**Untested components (all of them):**
- `src/components/CompanyPage/CompanyPage.js` — complex routing, data fetching, conditional rendering, chart rendering
- `src/components/NewsData/NewsData.js` — API fetch, loading state, empty state, data normalization logic
- `src/components/NewsItem/NewsItem.js` — nested data access with multiple fallback paths for title, link, and image
- `src/components/SearchBar/SearchBar.js` — MUI Autocomplete interaction and navigation behavior
- `src/components/TopCompanies/TopCompanies.js` — sort logic applied directly to context data (mutates order)
- `src/components/CompanyTicker/CompanyTicker.js` — conditional class logic for percent change direction
- `src/components/CustomSentiment/CustomSentiment.js` — form submission, async axios call, error display

**Untested utilities:**
- `src/utils/getStockData.js` — duplicate of api.js with different endpoint, no tests, not imported anywhere
- `src/apis/api.js` — URL construction logic (env var vs. fallback), error transformation

**Untested backend logic:**
- `backend/main.py` — all three FastAPI routes (`/stock-price`, `/news`, `/analyze-custom`), in-memory cache behavior, sentiment scoring, Qwen LLM integration, FinBERT pipeline
- `backend/news_preprocess.py` — `chunk_text`, `clean_text_column`, `rescale_sentiment_score`, `analyze_sentiment` functions are all pure and straightforwardly unit-testable but have no tests
- `backend/SentimentAnalysis.py` — AWS Comprehend integration, chunking aggregation logic

**No CI test gate:**
- The `amplify.yml` (AWS Amplify build config) runs only `npm run build`. Tests are not executed in any automated pipeline, meaning broken tests would never block a deployment.

---

*Testing analysis: 2026-03-26*
