---
phase: 01
plan: 01
subsystem: backend-security
tags: [security, cors, api-key, validation, pydantic]
dependency_graph:
  requires: []
  provides: [SEC-01, SEC-02, SEC-03, SEC-04]
  affects: [backend/main.py, backend/config.py, backend/requirements.txt]
tech_stack:
  added: [pydantic-settings]
  removed: [python-dotenv (from main.py only; still in requirements for now)]
  patterns: [pydantic-settings-config, fastapi-api-key-dependency, query-validation]
key_files:
  created:
    - backend/config.py
  modified:
    - backend/main.py
    - backend/requirements.txt
decisions:
  - "Use pydantic-settings for type-safe env var loading with @lru_cache singleton"
  - "Restrict CORS to explicit origins from ALLOWED_ORIGINS env (no wildcard + credentials)"
  - "Gate only /analyze-custom with API key (not /stock-price or /news) — keep public for portfolio reviewers"
  - "Validate text input with Query(max_length=2000) to prevent OOM on Qwen"
metrics:
  duration_minutes: 10
  completed_date: "2026-03-27"
  tasks_completed: 2
  files_changed: 3
---

# Phase 01 Plan 01: Backend Security Hardening Summary

**One-liner:** Eliminated three critical backend vulnerabilities: wildcard CORS with credentials, unauthenticated LLM endpoint, and unbounded text input; migrated from dotenv to pydantic-settings.

---

## What Was Built

The FastAPI backend now uses **pydantic-settings** for validated environment variable loading. The CORS middleware no longer uses a wildcard origin when credentials are enabled — it instead reads `ALLOWED_ORIGINS` from the environment and builds an explicit allow-list. The expensive `/analyze-custom` endpoint now requires a valid `X-API-Key` header (HTTP 403 on failure) and enforces a 2000-character limit on the `text` query parameter (HTTP 422 on overflow). The previous `dotenv` import and `load_dotenv()` call were removed; configuration is now injected via `Depends(get_settings)`.

---

## Tasks Completed

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Create backend/config.py with pydantic-settings | 363f7a4 | backend/config.py, backend/requirements.txt |
| 2 | Fix CORS, add API key auth, add input validation in main.py | 1ce3a7c | backend/main.py |

---

## Verification Results

All acceptance criteria passed:

- `grep -n 'allow_origins.*\*' backend/main.py` → zero matches (no wildcard CORS) **PASS**
- `grep -n 'allow_origins=_allowed_origins' backend/main.py` → one match (correct explicit origin list) **PASS**
- `grep -n 'require_api_key' backend/main.py` → ≥2 matches (definition + usage) **PASS**
- `grep -n 'max_length=2000' backend/main.py` → one match on analyze_custom **PASS**
- `grep -n 'load_dotenv' backend/main.py` → zero matches (removed) **PASS**
- `grep -n 'from config import' backend/main.py` → one match (pydantic-settings wired) **PASS**
- `python -c "import ast; ast.parse(open('backend/main.py').read())"` → exits 0 (syntax OK) **PASS**
- `backend/config.py` contains `class Settings(BaseSettings)` and `api_key: str` (required) **PASS**
- `backend/requirements.txt` contains `pydantic-settings>=2.0.0` **PASS**

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None. All security controls are fully implemented with no placeholder values.

---

## Self-Check: PASSED

- backend/config.py — FOUND (committed in 363f7a4)
- backend/main.py — FOUND (committed in 1ce3a7c)
- backend/requirements.txt — MODIFIED (pydantic-settings added)
- All acceptance criteria — VERIFIED
