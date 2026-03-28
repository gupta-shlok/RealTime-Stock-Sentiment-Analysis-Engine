---
phase: 4
slug: sentiment-intelligence-upgrade
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 (Wave 0 installs) |
| **Config file** | `backend/pytest.ini` — Wave 0 creates this |
| **Quick run command** | `pytest backend/tests/ -x -q` |
| **Full suite command** | `pytest backend/tests/ -v` |
| **Estimated runtime** | ~15 seconds (all mocked — no real model inference) |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/ -x -q`
- **After every plan wave:** Run `pytest backend/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | SENT-01 | infra | `pip install pytest pytest-asyncio==1.3.0` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | SENT-01 | infra | `pytest backend/tests/ -x -q` (after stubs) | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | SENT-01 | unit | `pytest backend/tests/test_finbert.py -x` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 1 | SENT-01 | unit | `pytest backend/tests/test_finbert.py::test_label_order -x` | ❌ W0 | ⬜ pending |
| 4-01-05 | 01 | 1 | SENT-02 | unit | `pytest backend/tests/test_aggregation.py -x` | ❌ W0 | ⬜ pending |
| 4-01-06 | 01 | 1 | SENT-02 | unit | `pytest backend/tests/test_aggregation.py::test_all_below_threshold -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | SENT-03 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_7d -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | SENT-03 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_30d -x` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 2 | SENT-03 | integration | `pytest backend/tests/test_endpoints.py::test_sentiment_trends_invalid_window -x` | ❌ W0 | ⬜ pending |
| 4-02-04 | 02 | 2 | SENT-04 | integration | `pytest backend/tests/test_endpoints.py::test_sector_sentiment_exclusion -x` | ❌ W0 | ⬜ pending |
| 4-02-05 | 02 | 2 | SENT-04 | integration | `pytest backend/tests/test_endpoints.py::test_sector_sentiment_inclusion -x` | ❌ W0 | ⬜ pending |
| 4-02-06 | 02 | 2 | SENT-05 | integration | `pytest backend/tests/test_endpoints.py::test_narrative_cache_hit -x` | ❌ W0 | ⬜ pending |
| 4-02-07 | 02 | 2 | SENT-05 | integration | `pytest backend/tests/test_endpoints.py::test_narrative_pending -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pip install pytest pytest-asyncio==1.3.0` — test framework not installed
- [ ] `backend/pytest.ini` — configure `asyncio_mode = auto`
- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures: mock `app.state.finbert_model`, mock `app.state.finbert_tokenizer`, pre-loaded `sentiment_scores.json`, `TestClient`
- [ ] `backend/tests/test_finbert.py` — stubs for SENT-01 (label order + score direction tests)
- [ ] `backend/tests/test_aggregation.py` — stubs for SENT-02 (weighted mean + threshold filtering)
- [ ] `backend/tests/test_endpoints.py` — stubs for SENT-03, SENT-04, SENT-05 endpoint tests

**Testing strategy note:** FinBERT and Qwen model inference MUST be mocked in all tests (no 30s model load per test run). Use `unittest.mock.patch` to replace `app.state.finbert_model` with a stub returning fixed logits `[0.7, 0.1, 0.2]` (strongly positive) for positive test cases.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Qwen narrative is coherent and cites specific headlines | SENT-05 | LLM output quality cannot be auto-verified | Call `GET /stock-narrative/AAPL`, poll until complete, inspect narrative text for headline references |
| Neutral rate drops after FinBERT upgrade | SENT-01 | Requires real news feed, not mocked | Run server against live `/news`, count `sentiment_label == "Neutral"` across 20 articles — expect < 60% |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
