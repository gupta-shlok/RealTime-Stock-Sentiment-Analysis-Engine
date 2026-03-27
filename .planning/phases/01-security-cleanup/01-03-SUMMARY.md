---
phase: 01-security-cleanup
plan: 03
subsystem: frontend
tags: [cleanup, aws, mui, dependencies, docker]
requirements: [CLEAN-01, CLEAN-02, CLEAN-03]

dependency_graph:
  requires: []
  provides: [clean-frontend-api-config, clean-dependencies, clean-dockerfile]
  affects: [frontend/stock_sentiment_analysis/src/apis/api.js, frontend/stock_sentiment_analysis/src/utils/getStockData.js, frontend/stock_sentiment_analysis/package.json, frontend/stock_sentiment_analysis/Dockerfile]

tech_stack:
  added: []
  removed: ["@material-ui/core@4.12.4", "aws-amplify@6.0.21", "@aws-amplify/ui-react@6.1.6"]
  patterns: ["REACT_APP_API_URL env-var-only pattern", "no ternary fallback to dead endpoints"]

key_files:
  created: []
  modified:
    - frontend/stock_sentiment_analysis/src/apis/api.js
    - frontend/stock_sentiment_analysis/src/utils/getStockData.js
    - frontend/stock_sentiment_analysis/package.json
    - frontend/stock_sentiment_analysis/Dockerfile

decisions:
  - "Direct REACT_APP_API_URL usage instead of ternary fallback — makes missing env var immediately visible as a broken request rather than silent routing to a dead AWS endpoint"
  - "Remove @material-ui/core (MUI v4) alongside aws-amplify to eliminate the peer dependency conflict that forced --legacy-peer-deps in Docker builds"

metrics:
  duration_minutes: 5
  completed_date: "2026-03-27"
  tasks_completed: 2
  files_changed: 4
---

# Phase 01 Plan 03: Frontend AWS Cleanup Summary

**One-liner:** Replaced two hardcoded AWS API Gateway URL fallbacks with exclusive REACT_APP_API_URL usage and removed MUI v4 + aws-amplify packages to eliminate the peer dependency conflict requiring --legacy-peer-deps.

---

## What Was Done

Removed all stale AWS infrastructure references from the React frontend. Two frontend files contained ternary expressions that silently fell back to decommissioned AWS API Gateway endpoints when `REACT_APP_API_URL` was absent. These have been replaced with direct env-var URL construction, so a missing env var now produces an immediate axios error rather than routing to a dead endpoint.

Three unused packages were removed from `package.json` — `@material-ui/core` (MUI v4), `aws-amplify`, and `@aws-amplify/ui-react` — none of which are imported anywhere in the source. With the MUI v4/v5 conflict eliminated, the Dockerfile no longer needs `--legacy-peer-deps`.

---

## Tasks Completed

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Remove hardcoded AWS URLs from api.js and getStockData.js | 0adb6e6 | src/apis/api.js, src/utils/getStockData.js |
| 2 | Remove unused dependencies from package.json and fix Dockerfile | 0cdb5c0 | package.json, Dockerfile |

---

## Verification Results

All 6 success criteria passed:

1. PASS: `grep -r "execute-api.amazonaws.com" frontend/stock_sentiment_analysis/src/` — zero matches (CLEAN-01)
2. PASS: `grep "@material-ui/core" package.json` — zero matches (CLEAN-02)
3. PASS: `grep "aws-amplify" package.json` — zero matches (CLEAN-03)
4. PASS: `grep "legacy-peer-deps" Dockerfile` — zero matches
5. PASS: Both api.js and getStockData.js reference REACT_APP_API_URL with no AWS fallback
6. PASS: package.json is valid JSON with exactly 14 dependencies

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None. All API calls are wired to REACT_APP_API_URL exclusively. No placeholder data or mock fallbacks remain.

---

## Self-Check

Checking files exist and commits are present...
