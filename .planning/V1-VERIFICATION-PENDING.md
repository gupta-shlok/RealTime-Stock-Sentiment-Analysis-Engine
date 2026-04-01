# v1.0 Verification Pending

Items to validate before considering v1.0 fully production-ready.

## Narrative Engine (Qwen)
- **Phase**: Phase 4 (Sentiment Intelligence Upgrade)
- **Endpoint**: `GET /stock-narrative/{ticker}`
- **Status**: Implemented but not tested
- **What to test**:
  1. Call `/stock-narrative/AAPL` → get `job_id`
  2. Poll `GET /stock-narrative/AAPL?job_id=<job_id>` until complete
  3. Verify narrative is coherent, references specific sentiment signals, not generic filler
  4. Test 3-5 tickers to ensure consistency
- **Acceptance**: Narratives should explain "why this stock is moving" with references to sentiment scores and headlines

---

*Captured: 2026-04-01*
*Deferred testing for later session*
